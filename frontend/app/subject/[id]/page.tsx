"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter, useParams } from "next/navigation";
import { useStudentId } from "@/hooks/useStudentId";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  ArrowLeft, Upload, FileText, Loader2, ArrowRight,
  CheckCircle, Brain, Activity, RadarIcon, RefreshCw, Zap
} from "lucide-react";
import {
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  Radar, ResponsiveContainer, Tooltip
} from "recharts";

type Topic = { id: number; name: string; description?: string };
type Document = { id: number; filename: string; chunks: number; uploaded_at: string };
type MasteryEntry = { topic: string; mastery: number };

export default function SubjectHubPage() {
  const router = useRouter();
  const params = useParams();
  const subjectId = Number(params.id);
  const studentId = useStudentId();

  const [subjectName, setSubjectName] = useState("");
  const [subjectKind, setSubjectKind] = useState<"custom" | "prebuilt">("custom");
  const [topics, setTopics] = useState<Topic[]>([]);
  const [docs, setDocs] = useState<Document[]>([]);
  const [radarData, setRadarData] = useState<MasteryEntry[]>([]);
  const [journey, setJourney] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"topics" | "radar" | "journey">("topics");

  // Upload state
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadMode, setUploadMode] = useState<"add" | "replace" | null>(null);
  const [replaceTargetId, setReplaceTargetId] = useState<number | null>(null);
  const [uploadResult, setUploadResult] = useState<string[] | null>(null);

  useEffect(() => {
    if (!studentId || !subjectId) return;
    loadAll();
  }, [studentId, subjectId]);

  const loadAll = async () => {
    setLoading(true);
    try {
      const [subjectsRes, topicsRes, docsRes, radarRes, journeyRes] = await Promise.all([
        api.get(`/subjects/${studentId}`),
        api.get(`/subjects/${subjectId}/topics`),
        api.get(`/subjects/${subjectId}/material-status`),
        api.get(`/mastery-radar/${studentId}`),
        api.get(`/learning-journey/${studentId}`, { params: { subject_id: subjectId } }),
      ]);

      const subject = subjectsRes.data.find((s: any) => s.id === subjectId);
      if (subject) {
        setSubjectName(subject.name);
        setSubjectKind(subject.kind);
      }

      setTopics(topicsRes.data);
      setDocs(docsRes.data.documents || []);

      const subjectRadar = radarRes.data.find((r: any) => r.subject_id === subjectId);
      setRadarData(subjectRadar?.data || []);

      setJourney(journeyRes.data.timeline || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const startTopic = (topic: Topic) => {
    localStorage.setItem("current_subject_id", String(subjectId));
    localStorage.setItem("current_subject_name", subjectName);
    localStorage.setItem("current_topic_name", topic.name);
    router.push("/tutor");
  };

  const startChallenge = () => {
    localStorage.setItem("current_subject_id", String(subjectId));
    localStorage.setItem("current_subject_name", subjectName);
    localStorage.setItem("challenge_mode", "true");
    router.push("/tutor");
  };

  const handleUpload = async () => {
    if (!file || !uploadMode) return;
    setUploading(true);
    setUploadResult(null);

    const formData = new FormData();
    formData.append("file", file);
    if (uploadMode === "replace" && replaceTargetId) {
      formData.append("replace_document_id", String(replaceTargetId));
    }

    try {
      const res = await api.post(`/subjects/${subjectId}/upload`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      let newTopics: Topic[] = [];
      try {
        const topicsRes = await api.get(`/subjects/${subjectId}/topics`);
        newTopics = topicsRes.data;
        setTopics(topicsRes.data);
      } catch {}

      setUploadResult(res.data.topics_extracted || newTopics.map((t: Topic) => t.name));
      setFile(null);
      setUploadMode(null);
      setReplaceTargetId(null);
      loadAll().catch(console.error);

    } catch (uploadErr: any) {
      const detail = uploadErr?.response?.data?.detail;
      alert(`Upload failed: ${detail || "Make sure the file is a valid PDF."}`);
    } finally {
      setUploading(false);
    }
  };

  const eventColor: Record<string, string> = {
    session_start: "bg-blue-500", misconception: "bg-red-500",
    breakthrough: "bg-green-500", struggle: "bg-orange-500",
  };
  const eventIcon: Record<string, string> = {
    session_start: "▶", misconception: "⚠", breakthrough: "★", struggle: "↓",
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="max-w-4xl mx-auto space-y-6">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" onClick={() => router.push("/dashboard")}>
              <ArrowLeft className="w-4 h-4" />
            </Button>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-bold">{subjectName}</h1>
                <Badge variant={subjectKind === "prebuilt" ? "secondary" : "outline"} className="text-xs">
                  {subjectKind === "prebuilt" ? "Prebuilt" : "Custom"}
                </Badge>
              </div>
              <p className="text-muted-foreground text-sm">
                {topics.length} topics · {docs.length} document{docs.length !== 1 ? "s" : ""}
              </p>
            </div>
          </div>
          <Button
            variant="outline"
            onClick={startChallenge}
            disabled={topics.length === 0}
            className="flex items-center gap-2"
          >
            <Zap className="w-4 h-4" /> Challenge me
          </Button>
        </div>

        {/* Tab switcher */}
        <div className="flex gap-2 border-b border-border pb-2">
          {[
            { key: "topics", label: "Topics", icon: Brain },
            { key: "radar", label: "Mastery Radar", icon: RadarIcon },
            { key: "journey", label: "Learning Journey", icon: Activity },
          ].map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => setActiveTab(key as any)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm transition-colors
                ${activeTab === key ? "bg-muted font-medium text-foreground" : "text-muted-foreground hover:text-foreground"}`}
            >
              <Icon className="w-3.5 h-3.5" /> {label}
            </button>
          ))}
        </div>

        {/* Topics tab */}
        {activeTab === "topics" && (
          <div className="space-y-4">

            {/* Upload section — only for custom subjects */}
            {subjectKind === "custom" && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <Upload className="w-4 h-4" /> Learning Material
                  </CardTitle>
                  <CardDescription>
                    {docs.length > 0
                      ? `${docs.length} document${docs.length !== 1 ? "s" : ""} uploaded · ${topics.length} topics extracted`
                      : "No material uploaded yet"}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {docs.length > 0 && (
                    <div className="space-y-1.5">
                      {docs.map((d, i) => (
                        <div key={i} className="flex items-center gap-2 text-sm text-muted-foreground">
                          <FileText className="w-3.5 h-3.5 shrink-0" />
                          <span className="truncate">{d.filename}</span>
                          <span className="text-xs shrink-0">· {d.chunks} chunks</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {uploadMode === null ? (
                    <div className="space-y-2">
                      <div className="flex gap-2">
                        <Button size="sm" variant="outline" onClick={() => setUploadMode("add")}>
                          <Upload className="w-3.5 h-3.5 mr-1.5" /> Add material
                        </Button>
                      </div>
                      {docs.length > 0 && (
                        <div className="space-y-1.5 pt-1">
                          <p className="text-xs text-muted-foreground">Or replace a specific document:</p>
                          {docs.map((d) => (
                            <div key={d.id} className="flex items-center justify-between text-sm px-2 py-1.5 rounded-md hover:bg-muted">
                              <span className="text-muted-foreground truncate flex items-center gap-1.5">
                                <FileText className="w-3.5 h-3.5 shrink-0" /> {d.filename}
                              </span>
                              <Button
                                size="sm" variant="ghost" className="h-6 text-xs shrink-0"
                                onClick={() => { setUploadMode("replace"); setReplaceTargetId(d.id); }}
                              >
                                <RefreshCw className="w-3 h-3 mr-1" /> Replace
                              </Button>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="space-y-3">
                      <div
                        className={`border-2 border-dashed rounded-lg p-5 text-center cursor-pointer transition-colors
                          ${file ? "border-primary bg-primary/5" : "border-border hover:border-primary/40"}`}
                        onClick={() => document.getElementById("hub-file-input")?.click()}
                      >
                        <input id="hub-file-input" type="file" accept=".pdf" className="hidden"
                          onChange={(e) => setFile(e.target.files?.[0] || null)} />
                        {file ? (
                          <div className="flex items-center justify-center gap-2 text-sm">
                            <FileText className="w-4 h-4 text-primary" />
                            <span className="font-medium">{file.name}</span>
                          </div>
                        ) : (
                          <p className="text-sm text-muted-foreground">
                            {uploadMode === "replace" ? "Click to select replacement PDF" : "Click to select PDF to add"}
                          </p>
                        )}
                      </div>
                      {uploadMode === "replace" && (
                        <p className="text-xs text-destructive">
                          ⚠ This will remove "{docs.find((d) => d.id === replaceTargetId)?.filename}" and its extracted topics, replacing them with topics from the new file.
                        </p>
                      )}
                      <div className="flex gap-2">
                        <Button size="sm" disabled={!file || uploading} onClick={handleUpload}>
                          {uploading ? <><Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" /> Processing...</> : "Upload"}
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => { setUploadMode(null); setFile(null); setReplaceTargetId(null); }}>Cancel</Button>
                      </div>
                    </div>
                  )}

                  {uploadResult && uploadResult.length > 0 && (
                    <div className="mt-2 p-3 rounded-lg bg-green-500/10 border border-green-500/20">
                      <p className="text-xs font-medium text-green-500 flex items-center gap-1.5 mb-1">
                        <CheckCircle className="w-3.5 h-3.5" /> {uploadResult.length} new topics extracted
                      </p>
                      <p className="text-xs text-muted-foreground">{uploadResult.join(", ")}</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Topic list */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">
                  {topics.length > 0 ? `${topics.length} Topics` : "No topics yet"}
                </CardTitle>
                <CardDescription>
                  {topics.length > 0 ? "Click any topic to start or continue a Socratic session." : subjectKind === "custom" ? "Upload a PDF above to extract topics." : "Topics should have been seeded — try refreshing."}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                {topics.map((t) => {
                  const mastery = radarData.find((r) => r.topic === t.name)?.mastery;
                  return (
                    <button
                      key={t.id}
                      onClick={() => startTopic(t)}
                      className="w-full text-left p-3 rounded-lg border border-border hover:border-primary hover:bg-muted transition-all flex items-center justify-between group"
                    >
                      <div className="min-w-0">
                        <p className="text-sm font-medium truncate">{t.name}</p>
                        {t.description && (
                          <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">{t.description}</p>
                        )}
                      </div>
                      <div className="flex items-center gap-2 shrink-0 ml-3">
                        {mastery !== undefined && (
                          <Badge variant={mastery >= 70 ? "default" : mastery >= 40 ? "secondary" : "outline"} className="text-xs">
                            {mastery}%
                          </Badge>
                        )}
                        <ArrowRight className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" />
                      </div>
                    </button>
                  );
                })}
              </CardContent>
            </Card>
          </div>
        )}

        {/* Radar tab */}
        {activeTab === "radar" && (
          <Card>
            <CardHeader>
              <CardTitle>{subjectName} — Mastery Radar</CardTitle>
              <CardDescription>Topic-by-topic mastery within this subject</CardDescription>
            </CardHeader>
            <CardContent>
              {radarData.length > 0 ? (
                <ResponsiveContainer width="100%" height={420}>
                  <RadarChart data={radarData.map((d) => ({
                    topic: d.topic.length > 14 ? d.topic.slice(0, 12) + "…" : d.topic,
                    mastery: d.mastery,
                  }))}>
                    <PolarGrid stroke="#3f3f46" />
                    <PolarAngleAxis dataKey="topic" tick={{ fill: "#a1a1aa", fontSize: 11 }} />
                    <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fill: "#71717a", fontSize: 10 }} axisLine={false} />
                    <Radar name="Mastery" dataKey="mastery" stroke="#a855f7" fill="#a855f7" fillOpacity={0.35} />
                    <Tooltip
                      contentStyle={{ background: "#18181b", border: "1px solid #3f3f46", borderRadius: 8 }}
                      formatter={(v: any) => [`${v}%`, "Mastery"]}
                    />
                  </RadarChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-muted-foreground text-sm text-center py-12">
                  No mastery data yet — start a tutoring session first.
                </p>
              )}
            </CardContent>
          </Card>
        )}

        {/* Journey tab */}
        {activeTab === "journey" && (
          <Card>
            <CardHeader>
              <CardTitle>{subjectName} — Learning Journey</CardTitle>
              <CardDescription>Chronological timeline for this subject</CardDescription>
            </CardHeader>
            <CardContent>
              {journey.length > 0 ? (
                <div className="relative pl-6 space-y-5">
                  <div className="absolute left-[7px] top-2 bottom-2 w-px bg-border" />
                  {journey.map((event: any, i: number) => (
                    <div key={i} className="relative">
                      <span className={`absolute -left-6 top-0.5 w-3.5 h-3.5 rounded-full ${eventColor[event.type] || "bg-zinc-500"}`} />
                      <div className="flex items-center gap-2 flex-wrap">
                        <Badge variant="outline" className="text-xs">{event.topic}</Badge>
                        <span className="text-xs text-muted-foreground">{new Date(event.timestamp).toLocaleString()}</span>
                      </div>
                      <p className="text-sm mt-0.5">
                        <span className="mr-1">{eventIcon[event.type] || "•"}</span>{event.label}
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-muted-foreground text-sm text-center py-8">
                  No learning events yet for this subject.
                </p>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}