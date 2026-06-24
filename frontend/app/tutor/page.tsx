"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { useStudentId } from "@/hooks/useStudentId";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Brain, Send, ArrowLeft, Lightbulb, AlertCircle, CheckCircle, Settings } from "lucide-react";
import MessageContent from "@/components/MessageContent";
import SourceCitations from "@/components/SourceCitations";
import VisualAidPreferences from "@/components/VisualAidPreferences";

type Message = {
  role: "tutor" | "student";
  content: string;
  type?: "question" | "feedback" | "misconception";
  plots?: any[];
  images?: any[];
  videos?: any[];
  sources?: any[];
};

type TopicSummary = { id: number; name: string; description?: string };

export default function TutorPage() {
  const router = useRouter();
  const studentId = useStudentId();

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [currentQuestionId, setCurrentQuestionId] = useState<number | null>(null);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [subjectId, setSubjectId] = useState<number | null>(null);
  const [subjectName, setSubjectName] = useState("");
  const [topic, setTopic] = useState<TopicSummary | null>(null);
  const [understanding, setUnderstanding] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [isChallengeMode, setIsChallengeMode] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const sessionStarted = useRef(false);
  const [visualAids, setVisualAids] = useState<("diagram" | "plot" | "image" | "video")[]>(["diagram", "plot", "image", "video"]);
  const [showPreferences, setShowPreferences] = useState(false);
  const [preferencesConfirmed, setPreferencesConfirmed] = useState(false);

  useEffect(() => {
    if (sessionStarted.current) return;
    if (!studentId) return;

    const subId = localStorage.getItem("current_subject_id");
    const subName = localStorage.getItem("current_subject_name");
    const topicName = localStorage.getItem("current_topic_name");
    const challengeMode = localStorage.getItem("challenge_mode") === "true";

    if (!subId || (!topicName && !challengeMode)) {
      router.push("/dashboard");
      return;
    }

    if (!preferencesConfirmed) {
      setShowPreferences(true);
      return; // wait for the user to confirm before actually starting
    }

    sessionStarted.current = true;
    setSubjectId(Number(subId));
    setSubjectName(subName || "");
    setIsChallengeMode(challengeMode);

    if (challengeMode) {
      localStorage.removeItem("challenge_mode"); // one-shot flag, consume it
      startChallengeSession(studentId, Number(subId));
    } else {
      api.get(`/subjects/${subId}/topics`)
        .then((res) => {
          const found = (res.data as TopicSummary[]).find((t) => t.name === topicName);
          if (!found) {
            setError(`Couldn't find topic "${topicName}" in this subject.`);
            return;
          }
          setTopic(found);
          startSession(studentId, Number(subId), found);
        })
        .catch(() => setError("Failed to load topic."));
    }
  }, [studentId, preferencesConfirmed]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const startSession = async (sid: number, subId: number, t: TopicSummary) => {
    setLoading(true);
    try {
      const res = await api.post("/generate-question-adaptive", {
        topic_id: t.id,
        student_id: sid,
        subject_id: subId,
      });
      setCurrentQuestionId(res.data.question_id);
      setSessionId(res.data.session_id);
      api.post("/sessions/preferences", { session_id: res.data.session_id, visual_aid_preferences: visualAids }).catch(() => {});
      setMessages([
        {
          role: "tutor",
          content: `Let's explore **${t.name}** together! I'll guide you with questions that build from recognition toward deeper understanding.`,
          type: "question",
        },
        { role: "tutor", content: res.data.question, type: "question" },
      ]);
    } catch {
      setError("Sorry, something went wrong starting this session.");
    } finally {
      setLoading(false);
    }
  };

  const startChallengeSession = async (sid: number, subId: number) => {
    setLoading(true);
    try {
      const res = await api.post(`/subjects/${subId}/challenge`, null, { params: { student_id: sid } });
      setCurrentQuestionId(res.data.question_id);
      setSessionId(res.data.session_id);
      api.post("/sessions/preferences", { session_id: res.data.session_id, visual_aid_preferences: visualAids }).catch(() => {});
      setTopic({ id: res.data.topic_id, name: res.data.topic_name });
      setMessages([
        {
          role: "tutor",
          content: `Challenge mode! I'll mix questions across all of **${subjectName}**, prioritizing what needs the most attention. First up:`,
          type: "question",
        },
        { role: "tutor", content: res.data.question, type: "question" },
      ]);
    } catch {
      setError("Sorry, something went wrong starting the challenge.");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    if (!input.trim() || !currentQuestionId || !studentId || !topic || !subjectId) return;
    const userMessage = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "student", content: userMessage }]);
    setLoading(true);
    setUnderstanding(null);

    try {
      const evalRes = await api.post("/evaluate-answer", {
        question_id: currentQuestionId,
        student_response: userMessage,
        student_id: studentId,
      });
      if (evalRes.data.rejected) {
        setMessages((prev) => [...prev, { role: "tutor", content: evalRes.data.feedback, type: "misconception" }]);
        setLoading(false);
        return; // do not advance, do not touch understanding state, question stays exactly as-is
      }

      const { feedback, understanding_level, misconception_detected,
              misconception_type, follow_up_needed, hint_level, resolved } = evalRes.data;
      setUnderstanding(understanding_level);

      const { plots: responsePlots, images: responseImages, videos: responseVideos, sources: responseSources } = evalRes.data;
      const feedbackType = hint_level === "full_explanation" ? "feedback" : misconception_detected ? "misconception" : "feedback";
      setMessages((prev) => [...prev, { role: "tutor", content: feedback, type: feedbackType, plots: responsePlots, images: responseImages, videos: responseVideos, sources: responseSources }]);

      if (!follow_up_needed) {
        // Attempt 1 or 2 — same question stays active, just show the hint and wait for retry
        // currentQuestionId is intentionally left unchanged
      } else if (resolved || hint_level === "full_explanation") {
        // Resolved correctly, OR attempt 3 explanation was just given — either way, move to a new question
        const qRes = isChallengeMode
          ? await api.post(`/subjects/${subjectId}/challenge`, null, { params: { student_id: studentId } })
          : await api.post("/generate-question-adaptive", {
              topic_id: topic.id, student_id: studentId, subject_id: subjectId, session_id: sessionId,
            });
        setCurrentQuestionId(qRes.data.question_id);
        if (isChallengeMode) setTopic({ id: qRes.data.topic_id, name: qRes.data.topic_name });
        setMessages((prev) => [...prev, { role: "tutor", content: qRes.data.question, type: "question" }]);
      } else {
        setMessages((prev) => [...prev, {
          role: "tutor",
          content: "Excellent! You've demonstrated great understanding of this topic.",
          type: "feedback",
        }]);
      }
    } catch {
      setMessages((prev) => [...prev, { role: "tutor", content: "Something went wrong. Please try again.", type: "feedback" }]);
    } finally {
      setLoading(false);
    }
  };

  const getMsgStyle = (msg: Message) => {
    if (msg.role === "student") return "bg-primary text-primary-foreground ml-auto";
    if (msg.type === "misconception") return "bg-destructive/10 border border-destructive/20";
    if (msg.type === "feedback") return "bg-green-500/10 border border-green-500/20";
    return "bg-muted";
  };

  const getMsgIcon = (msg: Message) => {
    if (msg.role === "student") return null;
    if (msg.type === "misconception") return <AlertCircle className="w-4 h-4 text-destructive shrink-0 mt-0.5" />;
    if (msg.type === "feedback") return <CheckCircle className="w-4 h-4 text-green-500 shrink-0 mt-0.5" />;
    return <Lightbulb className="w-4 h-4 text-primary shrink-0 mt-0.5" />;
  };

  if (showPreferences && messages.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6">
        <div className="max-w-sm w-full space-y-4">
          <h2 className="text-lg font-semibold text-center">Before we start</h2>
          <VisualAidPreferences
            selected={visualAids}
            onChange={setVisualAids}
            onConfirm={() => { setShowPreferences(false); setPreferencesConfirmed(true); }}
          />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 p-6 text-center">
        <AlertCircle className="w-8 h-8 text-destructive" />
        <p className="text-muted-foreground">{error}</p>
        <Button onClick={() => router.push("/dashboard")}>Back to Dashboard</Button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <div className="sticky top-0 z-20 bg-background border-b border-border p-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => router.push("/dashboard")}>
            <ArrowLeft className="w-4 h-4" />
          </Button>
          <Brain className="w-6 h-6 text-primary" />
          <div>
            <h1 className="font-semibold">{subjectName}</h1>
            <p className="text-xs text-muted-foreground">
              {isChallengeMode && <span className="text-primary">⚡ Challenge · </span>}{topic?.name}
            </p>
          </div>
        </div>
        {understanding && (
          <Badge variant={understanding === "excellent" ? "default" : understanding === "good" ? "secondary" : "outline"}>
            {understanding === "excellent" ? "🌟 Excellent" : understanding === "good" ? "✅ Good" : understanding === "partial" ? "📈 Improving" : "🔄 Keep Going"}
          </Badge>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4 max-w-3xl mx-auto w-full">
        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-2 ${msg.role === "student" ? "justify-end" : "justify-start"}`}>
            {msg.role === "tutor" && getMsgIcon(msg)}
            <div className={`rounded-2xl px-4 py-3 max-w-[80%] text-sm leading-relaxed ${getMsgStyle(msg)}`}>
              <MessageContent content={msg.content} plots={msg.plots} images={msg.images} videos={msg.videos} />
              {msg.sources && <SourceCitations sources={msg.sources} />}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex gap-2 justify-start">
            <Lightbulb className="w-4 h-4 text-primary shrink-0 mt-3" />
            <div className="bg-muted rounded-2xl px-4 py-3">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-primary/50 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                <span className="w-2 h-2 bg-primary/50 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                <span className="w-2 h-2 bg-primary/50 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="border-t border-border p-4">
        <div className="max-w-3xl mx-auto flex gap-3 items-end"> {/* Switched back to items-end to anchor layout properly */}
          <Button
            variant="ghost" 
            size="icon"
            onClick={() => setShowPreferences(true)}
            title="Visual aid preferences"
            className="shrink-0 h-[52px] w-[52px]" 
          >
            <Settings className="w-4 h-4" />
          </Button>
          
          <Textarea
            placeholder="Share your thoughts..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSubmit(); } }}
            className="resize-none min-h-[52px] max-h-32 flex-1"
            rows={2}
          />
          
          <Button 
            onClick={handleSubmit} 
            disabled={loading || !input.trim()} 
            size="icon" 
            className="shrink-0 h-[52px] w-[52px] rounded-lg" 
          >
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </div>


      {showPreferences && messages.length > 0 && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-6" onClick={() => setShowPreferences(false)}>
          <div className="bg-card border border-border rounded-xl p-5 max-w-sm w-full" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-sm font-semibold mb-3">Visual aid preferences</h3>
            <VisualAidPreferences
              selected={visualAids}
              onChange={(aids) => {
                setVisualAids(aids);
                if (sessionId) {
                  api.post("/sessions/preferences", { session_id: sessionId, visual_aid_preferences: aids }).catch(() => {});
                }
              }}
              compact
            />
            <Button size="sm" className="w-full mt-3" onClick={() => setShowPreferences(false)}>Done</Button>
          </div>
        </div>
      )}
    </div>
  );
}