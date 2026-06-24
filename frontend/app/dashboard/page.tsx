"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useSession, signOut } from "next-auth/react";
import { useStudentId } from "@/hooks/useStudentId";
import { api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Brain, Plus, Sparkles, ArrowRight, Network, Loader2,
  Flame, Clock, TrendingUp, Layers, AlertCircle, Trash2, X
} from "lucide-react";
import GoldThread from "@/components/GoldThread";
import { SubjectCrestIcon, SubjectWatermark, detectCategory } from "@/components/SubjectCrest";
import AnimatedCounter from "@/components/AnimatedCounter";
import { QuillIcon, MasteryIcon, NetworkNodeIcon, ManuscriptIcon } from "@/components/WeeklyAchievementIcons";
import KnowledgeGraphPreview from "@/components/KnowledgeGraphPreview";

type SubjectSummary = {
  id: number; name: string; kind: "custom" | "prebuilt";
  topic_count: number; topics_learned: number; overall_mastery: number;
  last_studied_at: string | null; last_topic: string | null; created_at: string;
};

type Overview = {
  total_subjects: number; study_streak_days: number; time_invested_minutes: number;
  weekly_questions_answered: number; topics_mastered_this_week: number;
  new_connections_this_week: number; new_topics_this_week: number;
  overall_knowledge_growth_pct: number;
};

type RevisionItem = {
  topic_id: number; topic_name: string; subject_id: number; subject_name: string;
  mastery: number; priority: number; reason: string;
};

export default function DashboardPage() {
  const router = useRouter();
  const { data: session } = useSession();
  const studentId = useStudentId();

  const [subjects, setSubjects] = useState<SubjectSummary[]>([]);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [revisionQueue, setRevisionQueue] = useState<RevisionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleteTarget, setDeleteTarget] = useState<SubjectSummary | null>(null);
  const [deleting, setDeleting] = useState(false);
  
  useEffect(() => {
  // 🟢 If studentId is not ready yet, wait (session still loading)
  if (studentId === undefined) return;

  // 🟢 NEW USER CASE → stop loading immediately
  if (!studentId) {
    setSubjects([]);
    setOverview(null);
    setRevisionQueue([]);
    setLoading(false);
    return;
  }

  Promise.all([
    api.get(`/subjects/${studentId}`),
    api.get(`/dashboard/${studentId}/overview`),
    api.get(`/dashboard/${studentId}/revision-queue`),
  ])
    .then(([subRes, ovRes, revRes]) => {
      setSubjects(subRes.data || []);
      setOverview(ovRes.data || null);
      setRevisionQueue(revRes.data || []);
    })
    .catch((err) => {
      console.error("Dashboard load failed:", err);

      // 🟢 IMPORTANT: unblock UI even if backend fails
      setSubjects([]);
      setOverview(null);
      setRevisionQueue([]);
    })
    .finally(() => setLoading(false));
}, [studentId]);

  const openSubject = (subject: SubjectSummary) => router.push(`/subject/${subject.id}`);

  const startRevision = (item: RevisionItem) => {
    localStorage.setItem("current_subject_id", String(item.subject_id));
    localStorage.setItem("current_topic_name", item.topic_name);
    router.push("/tutor");
  };

  const confirmDelete = async () => {
    if (!deleteTarget || !studentId) return;
    setDeleting(true);
    try {
      await api.delete(`/subjects/${deleteTarget.id}`, { params: { student_id: studentId } });
      setSubjects((prev) => prev.filter((s) => s.id !== deleteTarget.id));
      setDeleteTarget(null);
    } catch {
      alert("Failed to delete subject. Please try again.");
    } finally {
      setDeleting(false);
    }
  };

  const studentName = session?.user?.name || "there";

  const formatMinutes = (mins: number) => {
    if (mins < 60) return `${Math.round(mins)}m`;
    const h = Math.floor(mins / 60);
    const m = Math.round(mins % 60);
    return `${h}h ${m}m`;
  };

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="max-w-5xl mx-auto space-y-8">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Brain className="w-8 h-8 text-primary" />
            <div>
              <h1 className="text-2xl font-bold">Welcome back, {studentName}</h1>
              <p className="text-muted-foreground text-sm">Your learning cockpit</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => router.push("/knowledge")} className="flex items-center gap-2">
              <Network className="w-4 h-4" /> Knowledge Graph
            </Button>
            <Button variant="outline" size="sm" onClick={() => signOut({ callbackUrl: "/" })}>
              Sign Out
            </Button>
          </div>
        </div>

        {loading ? (
          <Card><CardContent className="pt-6 flex items-center justify-center text-muted-foreground gap-2">
            <Loader2 className="w-4 h-4 animate-spin" /> Loading your cockpit...
          </CardContent></Card>
        ) : (
          <>

            {/* Zone divider — Performance & Insights */}
            <div className="flex items-center gap-3">
              <span className="text-xs uppercase tracking-[0.2em] text-[#FFFFFF]/70 font-medium shrink-0">
                Performance & Insights
              </span>
              <div className="flex-1 h-px bg-gradient-to-r from-[#FFFFFF]/30 to-transparent" />
            </div>
            {/* Stat strip */}
            {overview && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                
                {/* Study Streak */}
                <div className="w-full text-left group relative overflow-hidden rounded-lg border border-[#1E293B]/50 hover:border-[#7FA3B8]/40 transition-colors pt-5 pb-4 px-4 bg-transparent">
                  <div className="flex items-center gap-2 text-muted-foreground text-xs mb-1">
                    <Flame className="w-3.5 h-3.5 text-orange-400" /> Study Streak
                  </div>
                  <p className="text-2xl font-bold">
                    {overview.study_streak_days}
                    <span className="text-sm text-muted-foreground font-normal"> days</span>
                  </p>
                </div>

                {/* Time Invested */}
                <div className="w-full text-left group relative overflow-hidden rounded-lg border border-[#1E293B]/50 hover:border-[#7FA3B8]/40 transition-colors pt-5 pb-4 px-4 bg-transparent">
                  <div className="flex items-center gap-2 text-muted-foreground text-xs mb-1">
                    <Clock className="w-3.5 h-3.5 text-blue-400" /> Time Invested
                  </div>
                  <p className="text-2xl font-bold">{formatMinutes(overview.time_invested_minutes)}</p>
                </div>

                {/* Knowledge Growth */}
                <div className="w-full text-left group relative overflow-hidden rounded-lg border border-[#1E293B]/50 hover:border-[#7FA3B8]/40 transition-colors pt-5 pb-4 px-4 bg-transparent">
                  <div className="flex items-center gap-2 text-muted-foreground text-xs mb-1">
                    <TrendingUp className="w-3.5 h-3.5 text-green-400" /> Knowledge Growth
                  </div>
                  <p className="text-2xl font-bold">{overview.overall_knowledge_growth_pct}%</p>
                </div>

                {/* Subjects */}
                <div className="w-full text-left group relative overflow-hidden rounded-lg border border-[#1E293B]/50 hover:border-[#7FA3B8]/40 transition-colors pt-5 pb-4 px-4 bg-transparent">
                  <div className="flex items-center gap-2 text-muted-foreground text-xs mb-1">
                    <Layers className="w-3.5 h-3.5 text-purple-400" /> Subjects
                  </div>
                  <p className="text-2xl font-bold">{overview.total_subjects}</p>
                </div>

              </div>
            )}


            {/* Weekly progress + revision queue side by side */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-4">
                {overview && (
                  <div className="w-full text-left group relative overflow-hidden rounded-lg border border-[#1E293B]/50 hover:border-[#7FA3B8]/40 transition-colors p-4 bg-transparent">
                    <div className="space-y-4">
                      <p className="text-base font-medium text-[#ffffff]/90 tracking-wide">This week's progress</p>
                      <div className="grid grid-cols-2 gap-4">
                        <div className="group flex items-start gap-2.5 p-2 -m-2 rounded-md transition-colors hover:bg-[#7FA3B8]/[0.06]">
                          <QuillIcon active={overview.weekly_questions_answered > 0} />
                          <div>
                            <p className="text-xl font-display"><AnimatedCounter value={overview.weekly_questions_answered} /></p>
                            <p className="text-xs text-muted-foreground">Questions answered</p>
                          </div>
                        </div>
                        <div className="group flex items-start gap-2.5 p-2 -m-2 rounded-md transition-colors hover:bg-[#7FA3B8]/[0.06]">
                          <MasteryIcon active={overview.topics_mastered_this_week > 0} />
                          <div>
                            <p className="text-xl font-display"><AnimatedCounter value={overview.topics_mastered_this_week} /></p>
                            <p className="text-xs text-muted-foreground">Topics mastered</p>
                          </div>
                        </div>
                        <div className="group flex items-start gap-2.5 p-2 -m-2 rounded-md transition-colors hover:bg-[#7FA3B8]/[0.06]">
                          <NetworkNodeIcon active={overview.new_connections_this_week > 0} />
                          <div>
                            <p className="text-xl font-display"><AnimatedCounter value={overview.new_connections_this_week} /></p>
                            <p className="text-xs text-muted-foreground">New connections</p>
                          </div>
                        </div>
                        <div className="group flex items-start gap-2.5 p-2 -m-2 rounded-md transition-colors hover:bg-[#7FA3B8]/[0.06]">
                          <ManuscriptIcon active={overview.new_topics_this_week > 0} />
                          <div>
                            <p className="text-xl font-display"><AnimatedCounter value={overview.new_topics_this_week} /></p>
                            <p className="text-xs text-muted-foreground">New topics added</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
                <KnowledgeGraphPreview studentId={studentId} />
              </div>

              <div className="w-full text-left group relative overflow-hidden rounded-lg border border-[#1E293B]/50 hover:border-[#7FA3B8]/40 transition-colors p-4 bg-transparent">
                <div className="space-y-3">
                  <p className="text-base font-medium text-[#FFFFFF]/90 tracking-wide">Revision queue</p>
                  {revisionQueue.length === 0 ? (
                    <p className="text-sm text-muted-foreground py-2">Nothing needs revision right now — nice work.</p>
                  ) : (
                    <div className="space-y-1.5">
                      {revisionQueue.slice(0, 5).map((item) => (
                        <button
                          key={item.topic_id}
                          onClick={() => startRevision(item)}
                          className="w-full flex items-center justify-between text-sm px-2 py-2 -mx-2 rounded-md transition-colors hover:bg-[#7FA3B8]/[0.06] text-left"
                        >
                          <div className="min-w-0">
                            <p className="font-medium truncate">{item.topic_name}</p>
                            <p className="text-xs text-muted-foreground truncate">{item.subject_name} · {item.reason}</p>
                          </div>
                          <Badge variant="outline" className="text-xs shrink-0 ml-2 border-[#7FA3B8]/30 text-[#7FA3B8]/80">{item.mastery}%</Badge>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>


            {/* Zone divider — separates Performance & Insights from Learning Domains */}
            <div className="flex items-center gap-3 pt-2">
              <span className="text-xs uppercase tracking-[0.2em] text-[#FFFFFF]/70 font-medium shrink-0">
                Learning Domains
              </span>
              <div className="flex-1 h-px bg-gradient-to-r from-[#FFFFFF]/30 to-transparent" />
            </div>
            
            {/* Subjects */}
            {subjects.length === 0 ? (
              <Card className="border-dashed">
                <CardContent className="pt-10 pb-10 text-center space-y-4">
                  <Sparkles className="w-10 h-10 text-primary mx-auto" />
                  <div>
                    <p className="font-medium text-lg">No subjects yet</p>
                    <p className="text-muted-foreground text-sm mt-1">Bring your own material, or start from a ready-made domain.</p>
                  </div>
                  <Button onClick={() => router.push("/learn/setup")} className="mt-2">
                    <Plus className="w-4 h-4 mr-2" /> Set Up Your First Subject
                  </Button>
                </CardContent>
              </Card>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {subjects.map((s) => (
                  <Card key={s.id} className="hover:border-[#D4A574]/40 transition-all duration-300 hover:-translate-y-0.5 group relative overflow-hidden">
                    <SubjectWatermark category={detectCategory(s.name)} />

                    <Button
                      size="icon" variant="ghost"
                      className="absolute top-3 right-3 h-7 w-7 z-10 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive"
                      onClick={(e) => { e.stopPropagation(); setDeleteTarget(s); }}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>

                    <CardContent className="pt-6 space-y-3 relative z-[1]">
                      <div className="flex items-start justify-between pr-8">
                        <div className="flex items-center gap-2.5">
                          <SubjectCrestIcon category={detectCategory(s.name)} className="w-7 h-7 transition-transform duration-300 group-hover:scale-110" />
                          <h3 className="font-semibold">{s.name}</h3>
                        </div>
                        <Badge variant={s.kind === "prebuilt" ? "secondary" : "outline"} className="text-xs">
                          {s.kind === "prebuilt" ? "Prebuilt" : "Custom"}
                        </Badge>
                      </div>

                      <div className="space-y-2.5">
                        <GoldThread
                          value={s.overall_mastery}
                          sublabel={`${s.topics_learned}/${s.topic_count} topics learned`}
                          accent="gold"
                        />
                        {s.last_studied_at && (
                          <p className="text-xs text-muted-foreground">
                            Last active {new Date(s.last_studied_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
                            {s.last_topic && <> · {s.last_topic}</>}
                          </p>
                        )}
                      </div>

                      <Button size="sm" className="w-full" onClick={() => openSubject(s)}>
                        Open <ArrowRight className="w-3.5 h-3.5 ml-1.5" />
                      </Button>
                    </CardContent>
                  </Card>
                ))}

                <Card
                  className="border-dashed hover:border-primary/50 transition-colors cursor-pointer"
                  onClick={() => router.push("/learn/setup")}
                >
                  <CardContent className="pt-6 h-full flex flex-col items-center justify-center text-center gap-2 min-h-[140px]">
                    <Plus className="w-6 h-6 text-muted-foreground" />
                    <p className="text-sm font-medium">New Subject</p>
                  </CardContent>
                </Card>
              </div>
            )}
          </>
        )}
      </div>

      {/* Delete confirmation modal */}
      {deleteTarget && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-6" onClick={() => !deleting && setDeleteTarget(null)}>
          <Card className="max-w-sm w-full" onClick={(e) => e.stopPropagation()}>
            <CardContent className="pt-6 space-y-4">
              <div className="flex items-start justify-between">
                <p className="font-semibold">Delete "{deleteTarget.name}"?</p>
                <Button size="icon" variant="ghost" className="h-6 w-6" onClick={() => setDeleteTarget(null)}><X className="w-4 h-4" /></Button>
              </div>
              <p className="text-sm text-muted-foreground">
                This permanently removes all {deleteTarget.topic_count} topics, mastery scores, sessions, and learning history for this subject. This cannot be undone.
              </p>
              <div className="flex gap-2">
                <Button variant="destructive" className="flex-1" onClick={confirmDelete} disabled={deleting}>
                  {deleting ? <Loader2 className="w-4 h-4 animate-spin" /> : "Delete permanently"}
                </Button>
                <Button variant="outline" onClick={() => setDeleteTarget(null)} disabled={deleting}>Cancel</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}