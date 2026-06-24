"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useStudentId } from "@/hooks/useStudentId";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  ArrowLeft, BookOpen, Sparkles, Upload, FileText,
  CheckCircle, Loader2, ArrowRight, Library
} from "lucide-react";

type Step = "choose" | "custom-name" | "custom-upload" | "custom-topics" | "prebuilt-pick" | "prebuilt-topics";

type PrebuiltDomain = {
  id: number;
  name: string;
  slug: string;
  description: string;
  icon: string;
  topic_count: number;
};

export default function LearningSetupPage() {
  const router = useRouter();
  const studentId = useStudentId();
  const searchParams = useSearchParams();
  const [step, setStep] = useState<Step>("choose");

  const [subjectName, setSubjectName] = useState("");
  const [subjectId, setSubjectId] = useState<number | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [extractedTopics, setExtractedTopics] = useState<{ name: string; description?: string }[]>([]);

  const [domains, setDomains] = useState<PrebuiltDomain[]>([]);
  const [creatingDomain, setCreatingDomain] = useState<number | null>(null);
  const [prebuiltTopics, setPrebuiltTopics] = useState<{ name: string; description?: string }[]>([]);
  const [prebuiltSubjectName, setPrebuiltSubjectName] = useState("");

  useEffect(() => {
    if (!studentId) return;

    const pickTopicSubjectId = searchParams.get("subject_id");
    const shouldPickTopic = searchParams.get("pick_topic") === "true";

    if (pickTopicSubjectId && shouldPickTopic) {
      const name = localStorage.getItem("current_subject_name") || "";
      setPrebuiltSubjectName(name);
      setSubjectId(Number(pickTopicSubjectId));
      api.get(`/subjects/${pickTopicSubjectId}/topics`)
        .then((res) => {
          setPrebuiltTopics(res.data);
          setStep("prebuilt-topics");
        })
        .catch(console.error);
    }
  }, [studentId]);

  const createCustomSubject = async () => {
    if (!subjectName.trim() || !studentId) return;
    const res = await api.post("/subjects/custom", { student_id: studentId, name: subjectName.trim() });
    setSubjectId(res.data.subject_id);
    setStep("custom-upload");
  };

  const uploadMaterial = async () => {
    if (!file || !subjectId) return;
    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);
    formData.append("replace_existing", "false");
    try {
      await api.post(`/subjects/${subjectId}/upload`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const topicsRes = await api.get(`/subjects/${subjectId}/topics`);
      setExtractedTopics(topicsRes.data);
      setStep("custom-topics");
    } catch {
      alert("Upload failed. Make sure the file is a valid PDF.");
    } finally {
      setUploading(false);
    }
  };

  const startCustomSession = (topicName: string) => {
    localStorage.setItem("current_subject_id", String(subjectId));
    localStorage.setItem("current_subject_name", subjectName);
    localStorage.setItem("current_topic_name", topicName);
    router.push("/tutor");
  };

  useEffect(() => {
    if (step === "prebuilt-pick" && domains.length === 0) {
      api.get("/prebuilt-domains").then((res) => setDomains(res.data));
    }
  }, [step]);

  const choosePrebuilt = async (domain: PrebuiltDomain) => {
    if (!studentId) return;
    setCreatingDomain(domain.id);
    try {
      const res = await api.post("/subjects/prebuilt", { student_id: studentId, prebuilt_domain_id: domain.id });
      router.push(`/subject/${res.data.subject_id}`);
    } finally {
      setCreatingDomain(null);
    }
  };

  const Header = ({ title, onBack }: { title: string; onBack: () => void }) => (
    <div className="flex items-center gap-3 mb-8">
      <Button variant="ghost" size="icon" onClick={onBack}>
        <ArrowLeft className="w-4 h-4" />
      </Button>
      <h1 className="text-xl font-semibold">{title}</h1>
    </div>
  );

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="max-w-2xl mx-auto">

        {step === "choose" && (
          <>
            <Header title="Set up a subject" onBack={() => router.push("/dashboard")} />
            <div className="grid gap-4">
              <Card className="cursor-pointer hover:border-primary/50 transition-colors" onClick={() => setStep("custom-name")}>
                <CardContent className="pt-6 flex items-start gap-4">
                  <Sparkles className="w-6 h-6 text-primary shrink-0 mt-1" />
                  <div>
                    <h3 className="font-semibold mb-1">Custom Learning</h3>
                    <p className="text-sm text-muted-foreground">
                      Define your own subject — Polity, Machine Learning, anything — and upload your own material to ground it.
                    </p>
                  </div>
                </CardContent>
              </Card>
              <Card className="cursor-pointer hover:border-primary/50 transition-colors" onClick={() => setStep("prebuilt-pick")}>
                <CardContent className="pt-6 flex items-start gap-4">
                  <Library className="w-6 h-6 text-primary shrink-0 mt-1" />
                  <div>
                    <h3 className="font-semibold mb-1">Prebuilt Domain</h3>
                    <p className="text-sm text-muted-foreground">
                      Start instantly with a ready-made domain — Physics, Finance, AI, and more — already mapped into topics.
                    </p>
                  </div>
                </CardContent>
              </Card>
            </div>
          </>
        )}

        {step === "custom-name" && (
          <>
            <Header title="Name your subject" onBack={() => setStep("choose")} />
            <Card>
              <CardHeader>
                <CardTitle>What do you want to learn?</CardTitle>
                <CardDescription>e.g. Polity, Machine Learning, Economics, History</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Input
                  placeholder="Subject name"
                  value={subjectName}
                  onChange={(e) => setSubjectName(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && createCustomSubject()}
                  autoFocus
                />
                <Button className="w-full" disabled={!subjectName.trim()} onClick={createCustomSubject}>
                  Continue <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </CardContent>
            </Card>
          </>
        )}

        {step === "custom-upload" && (
          <>
            <Header title={`Upload material for ${subjectName}`} onBack={() => setStep("custom-name")} />
            <Card>
              <CardHeader>
                <CardTitle>Upload a PDF</CardTitle>
                <CardDescription>Topics will be extracted automatically from what you upload.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div
                  className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors
                    ${file ? "border-primary bg-primary/5" : "border-border hover:border-primary/50"}`}
                  onClick={() => document.getElementById("setup-file-input")?.click()}
                >
                  <input id="setup-file-input" type="file" accept=".pdf" className="hidden"
                    onChange={(e) => setFile(e.target.files?.[0] || null)} />
                  {file ? (
                    <div className="space-y-2">
                      <FileText className="w-8 h-8 text-primary mx-auto" />
                      <p className="font-medium text-sm">{file.name}</p>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <Upload className="w-8 h-8 text-muted-foreground mx-auto" />
                      <p className="text-sm font-medium">Click to select a PDF</p>
                    </div>
                  )}
                </div>
                <Button className="w-full" disabled={!file || uploading} onClick={uploadMaterial}>
                  {uploading ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Processing & extracting topics...</> : <>Continue <ArrowRight className="w-4 h-4 ml-2" /></>}
                </Button>
              </CardContent>
            </Card>
          </>
        )}

        {step === "custom-topics" && (
          <>
            <Header title={`${subjectName} — topics found`} onBack={() => setStep("custom-upload")} />
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <CheckCircle className="w-5 h-5 text-green-500" /> {extractedTopics.length} topics extracted
                </CardTitle>
                <CardDescription>Pick one to start your first Socratic session.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                {extractedTopics.map((t) => (
                  <button
                    key={t.name}
                    onClick={() => startCustomSession(t.name)}
                    className="w-full text-left p-3 rounded-lg border border-border hover:border-primary hover:bg-muted transition-all flex items-center justify-between group"
                  >
                    <div>
                      <p className="text-sm font-medium">{t.name}</p>
                      {t.description && <p className="text-xs text-muted-foreground mt-0.5">{t.description}</p>}
                    </div>
                    <ArrowRight className="w-4 h-4 text-muted-foreground group-hover:text-primary shrink-0 ml-3" />
                  </button>
                ))}
              </CardContent>
            </Card>
          </>
        )}

        {step === "prebuilt-pick" && (
          <>
            <Header title="Choose a domain" onBack={() => setStep("choose")} />
            {domains.length === 0 ? (
              <div className="flex justify-center py-12"><Loader2 className="w-5 h-5 animate-spin text-muted-foreground" /></div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {domains.map((d) => (
                  <Card key={d.id} className="hover:border-primary/50 transition-colors">
                    <CardContent className="pt-5 space-y-2">
                      <div className="flex items-center justify-between">
                        <BookOpen className="w-5 h-5 text-primary" />
                        <Badge variant="outline" className="text-xs">{d.topic_count} topics</Badge>
                      </div>
                      <h3 className="font-semibold">{d.name}</h3>
                      <p className="text-xs text-muted-foreground">{d.description}</p>
                      <Button
                        size="sm"
                        className="w-full mt-2"
                        disabled={creatingDomain === d.id}
                        onClick={() => choosePrebuilt(d)}
                      >
                        {creatingDomain === d.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : "Start"}
                      </Button>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </>
        )}

        {step === "prebuilt-topics" && (
          <>
            <Header title={`${prebuiltSubjectName} — pick a topic`} onBack={() => setStep("prebuilt-pick")} />
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <CheckCircle className="w-5 h-5 text-green-500" /> {prebuiltTopics.length} topics ready
                </CardTitle>
                <CardDescription>Pick one to start your first Socratic session.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                {prebuiltTopics.map((t) => (
                  <button
                    key={t.name}
                    onClick={() => {
                      localStorage.setItem("current_subject_id", String(subjectId));
                      localStorage.setItem("current_subject_name", prebuiltSubjectName);
                      localStorage.setItem("current_topic_name", t.name);
                      router.push("/tutor");
                    }}
                    className="w-full text-left p-3 rounded-lg border border-border hover:border-primary hover:bg-muted transition-all flex items-center justify-between group"
                  >
                    <div>
                      <p className="text-sm font-medium">{t.name}</p>
                      {t.description && <p className="text-xs text-muted-foreground mt-0.5">{t.description}</p>}
                    </div>
                    <ArrowRight className="w-4 h-4 text-muted-foreground group-hover:text-primary shrink-0 ml-3" />
                  </button>
                ))}
              </CardContent>
            </Card>
          </>
        )}

      </div>
    </div>
  );
}