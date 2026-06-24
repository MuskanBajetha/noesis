"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Brain, Upload, FileText, CheckCircle, ArrowLeft, Loader2 } from "lucide-react";
import axios from "axios";

const TOPICS = [
  "Newton's Laws", "Gravity", "Photosynthesis", "Cell Division",
  "Algebra", "Thermodynamics", "Evolution", "Quantum Physics", "Radar", "Custom"
];

export default function UploadPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [topic, setTopic] = useState("");
  const [customTopic, setCustomTopic] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState("");

  const handleUpload = async () => {
    const selectedTopic = topic === "Custom" ? customTopic : topic;
    if (!file || !selectedTopic) {
      setError("Please select a file and topic");
      return;
    }

    setLoading(true);
    setError("");

    const formData = new FormData();
    formData.append("file", file);
    formData.append("topic", selectedTopic);

    try {
      const res = await axios.post("http://127.0.0.1:8000/api/upload-pdf", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setResult(res.data);
    } catch {
      setError("Upload failed. Make sure the backend is running.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="max-w-2xl mx-auto space-y-6">

        {/* Header */}
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => router.push("/dashboard")}>
            <ArrowLeft className="w-4 h-4" />
          </Button>
          <Brain className="w-7 h-7 text-primary" />
          <div>
            <h1 className="text-2xl font-bold">Upload Learning Material</h1>
            <p className="text-muted-foreground text-sm">Add PDFs to ground the AI tutor in real content</p>
          </div>
        </div>

        {/* Upload Card */}
        <Card>
          <CardHeader>
            <CardTitle>Upload a PDF</CardTitle>
            <CardDescription>
              The AI will use this material to ask questions grounded in your actual learning content
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">

            {/* File Drop Zone */}
            <div
              className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors
                ${file ? "border-primary bg-primary/5" : "border-border hover:border-primary/50 hover:bg-muted/50"}`}
              onClick={() => document.getElementById("file-input")?.click()}
            >
              <input
                id="file-input"
                type="file"
                accept=".pdf"
                className="hidden"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
              {file ? (
                <div className="space-y-2">
                  <FileText className="w-10 h-10 text-primary mx-auto" />
                  <p className="font-medium">{file.name}</p>
                  <p className="text-sm text-muted-foreground">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                  <Badge variant="secondary">Ready to upload</Badge>
                </div>
              ) : (
                <div className="space-y-2">
                  <Upload className="w-10 h-10 text-muted-foreground mx-auto" />
                  <p className="font-medium">Click to select a PDF</p>
                  <p className="text-sm text-muted-foreground">Textbooks, lecture notes, research papers</p>
                </div>
              )}
            </div>

            {/* Topic Selection */}
            <div className="space-y-3">
              <label className="text-sm font-medium">Select Topic</label>
              <div className="grid grid-cols-3 gap-2">
                {TOPICS.map((t) => (
                  <button
                    key={t}
                    onClick={() => setTopic(t)}
                    className={`p-2 rounded-lg border text-sm transition-all
                      ${topic === t
                        ? "border-primary bg-primary text-primary-foreground"
                        : "border-border hover:border-primary/50"
                      }`}
                  >
                    {t}
                  </button>
                ))}
              </div>
              {topic === "Custom" && (
                <input
                  type="text"
                  placeholder="Enter custom topic name..."
                  value={customTopic}
                  onChange={(e) => setCustomTopic(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:border-primary"
                />
              )}
            </div>

            {error && <p className="text-destructive text-sm">{error}</p>}

            <Button
              className="w-full"
              onClick={handleUpload}
              disabled={loading || !file || !topic}
            >
              {loading ? (
                <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Processing PDF...</>
              ) : (
                <><Upload className="w-4 h-4 mr-2" /> Upload & Process</>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Success Result */}
        {result && result.status === "success" && (
          <Card className="border-green-500/30 bg-green-500/5">
            <CardContent className="pt-6">
              <div className="flex items-start gap-3">
                <CheckCircle className="w-6 h-6 text-green-500 shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <p className="font-semibold text-green-500">PDF Processed Successfully!</p>
                  <p className="text-sm text-muted-foreground">
                    <span className="font-medium text-foreground">{result.chunks_stored}</span> knowledge chunks stored for topic:{" "}
                    <span className="font-medium text-foreground">{result.topic}</span>
                  </p>
                  <p className="text-xs text-muted-foreground">Source: {result.source}</p>
                  <Button
                    variant="outline"
                    size="sm"
                    className="mt-3"
                    onClick={() => {
                      localStorage.setItem("current_topic", result.topic);
                      router.push("/tutor");
                    }}
                  >
                    Start Tutoring Session on {result.topic} →
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

      </div>
    </div>
  );
}