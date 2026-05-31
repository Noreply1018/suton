"use client";

import { ChangeEvent, FormEvent, ReactNode, useEffect, useMemo, useState } from "react";
import {
  BarChart3,
  BookOpen,
  Boxes,
  CheckCircle2,
  CircleDot,
  FileSearch,
  FileText,
  FileUp,
  Loader2,
  Plus,
  Search,
  Settings,
  ShieldCheck,
  SquareArrowOutUpRight,
  Target
} from "lucide-react";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

type Project = {
  id: number;
  name: string;
  document_count: number;
  question_count: number;
  latest_status: string;
};

type DocumentRow = {
  id: number;
  filename: string;
  page_count: number | null;
  status: string;
  failure_reason: string | null;
};

type Match = {
  id: number;
  rank: number;
  score: number;
  hit_reason: string;
  source_text: string;
  page_no: number;
  filename: string;
  pdf_url: string;
};

type QuestionResult = {
  question: { id: number; text: string; status: string };
  matches: Match[];
};

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${apiUrl}${path}`, {
    ...options,
    headers: options?.body instanceof FormData ? options.headers : { "Content-Type": "application/json", ...options?.headers }
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(body.detail ?? response.statusText);
  }
  return response.json();
}

export default function Home() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProjectId, setActiveProjectId] = useState<number | null>(null);
  const [documents, setDocuments] = useState<DocumentRow[]>([]);
  const [projectName, setProjectName] = useState("高等数学（上）期末复习");
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<QuestionResult | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const activeProject = useMemo(
    () => projects.find((project) => project.id === activeProjectId) ?? projects[0],
    [activeProjectId, projects]
  );
  const sourcedMatches = useMemo(() => result?.matches.filter(hasSource) ?? [], [result]);

  async function refresh(preferredProjectId?: number) {
    const nextProjects = await request<Project[]>("/projects");
    setProjects(nextProjects);
    const nextActive = preferredProjectId ?? activeProjectId ?? nextProjects[0]?.id ?? null;
    setActiveProjectId(nextActive);
    if (nextActive) {
      setDocuments(await request<DocumentRow[]>(`/projects/${nextActive}/documents`));
    } else {
      setDocuments([]);
    }
  }

  useEffect(() => {
    refresh().catch((err: Error) => setError(err.message));
    const questionId = new URLSearchParams(window.location.search).get("questionId");
    if (questionId) {
      request<QuestionResult>(`/questions/${questionId}`)
        .then(setResult)
        .catch((err: Error) => setError(err.message));
    }
    const timer = window.setInterval(() => {
      refresh().catch(() => undefined);
    }, 5000);
    return () => window.clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function createProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      const project = await request<Project>("/projects", {
        method: "POST",
        body: JSON.stringify({ name: projectName })
      });
      setActiveProjectId(project.id);
      await refresh(project.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建项目失败");
    } finally {
      setBusy(false);
    }
  }

  async function uploadFile(event: ChangeEvent<HTMLInputElement>) {
    if (!activeProject || !event.target.files?.[0]) return;
    setError("");
    const formData = new FormData();
    formData.append("file", event.target.files[0]);
    setBusy(true);
    try {
      await request(`/projects/${activeProject.id}/documents`, { method: "POST", body: formData });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "上传失败");
    } finally {
      event.target.value = "";
      setBusy(false);
    }
  }

  async function submitQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!activeProject) return;
    setError("");
    setResult(null);
    setBusy(true);
    try {
      const nextResult = await request<QuestionResult>(`/projects/${activeProject.id}/questions`, {
        method: "POST",
        body: JSON.stringify({ text: question })
      });
      setResult(nextResult);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "检索失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="min-h-screen overflow-hidden bg-paper text-ink" data-testid="app-shell">
      <div className="grid min-h-screen grid-cols-[240px_minmax(520px,1fr)_420px] max-2xl:grid-cols-[220px_minmax(460px,1fr)_380px] max-xl:grid-cols-1">
        <aside
          className="flex min-h-screen flex-col border-r border-teal-soft bg-[#f5f2ea]/95 px-4 py-6 max-xl:min-h-0 max-xl:border-b max-xl:border-r-0"
          data-testid="sidebar-nav"
        >
          <div className="mb-8 flex items-center gap-3">
            <div className="suton-mark">
              <CircleDot size={28} />
            </div>
            <div>
              <h1 className="text-2xl font-semibold text-[#0d5f6b]">Suton</h1>
              <p className="text-xs text-ink/55">溯源至证，问见真实</p>
            </div>
          </div>

          <nav className="space-y-2">
            <NavigationItem icon={<Boxes size={18} />} title="项目" subtitle="Projects" />
            <NavigationItem icon={<BookOpen size={18} />} title="材料库" subtitle="Materials" />
            <NavigationItem active icon={<Target size={18} />} title="溯源请求" subtitle="Trace Requests" />
            <NavigationItem icon={<FileSearch size={18} />} title="证据审阅" subtitle="Evidence Review" />
            <NavigationItem muted icon={<BarChart3 size={18} />} title="覆盖分析" subtitle="Coverage Analysis" />
            <NavigationItem icon={<Settings size={18} />} title="设置" subtitle="Settings" />
          </nav>

          <form onSubmit={createProject} className="mt-8 space-y-3 border-y border-teal-soft py-5">
            <label className="text-sm font-semibold" htmlFor="project-name">
              新建项目
            </label>
            <input
              id="project-name"
              value={projectName}
              onChange={(event) => setProjectName(event.target.value)}
              className="focus-ring w-full rounded-md border border-teal-soft bg-white/85 px-3 py-2 text-sm"
            />
            <button
              disabled={busy}
              className="focus-ring flex w-full items-center justify-center gap-2 rounded-md bg-accent px-3 py-2 text-sm font-semibold text-white disabled:opacity-55"
            >
              <Plus size={16} />
              创建项目
            </button>
          </form>

          <div className="mt-5 min-h-0 flex-1 space-y-2 overflow-auto">
            {projects.map((project) => (
              <button
                key={project.id}
                onClick={() => setActiveProjectId(project.id)}
                className={`focus-ring w-full rounded-md px-3 py-3 text-left text-sm transition ${
                  activeProject?.id === project.id ? "bg-white text-ink shadow-sm ring-1 ring-teal-soft" : "hover:bg-white/70"
                }`}
              >
                <span className="block truncate font-semibold">{project.name}</span>
                <span className="mt-1 block text-xs text-ink/55">
                  {project.document_count} 份资料 · {project.question_count} 道题
                </span>
              </button>
            ))}
          </div>

          <div className="mt-6 rounded-md border border-[#9ac8ca] bg-[#e9f5f3] p-4 text-sm text-[#0b6570]">
            <div className="mb-3 flex items-center gap-2 font-semibold">
              <ShieldCheck size={18} />
              仅基于已上传资料
            </div>
            <p className="text-xs leading-5 text-[#41757a]">系统只展示可追溯来源，不生成无来源答案。</p>
          </div>
        </aside>

        <section className="relative flex min-h-screen flex-col px-8 py-7 max-xl:min-h-0 max-md:px-5" data-testid="trace-workspace">
          <div className="paper-grid" aria-hidden="true" />

          <div className="relative z-10 mb-5 flex items-start justify-between gap-6 max-md:flex-col">
            <div>
              <p className="mb-2 text-sm font-medium text-[#1f8b91]">当前请求 · 今天</p>
              <h2 className="max-w-4xl text-balance text-3xl font-semibold leading-tight tracking-normal text-[#183a3d]">
                {question.trim() || "解释并找出不确定性原理的数学表达及其物理含义的出处。"}
              </h2>
              <div className="mt-4 flex flex-wrap items-center gap-3 text-xs font-medium text-[#1f6b70]">
                <span className="rounded-full bg-white/80 px-3 py-1 ring-1 ring-teal-soft">请求类型：概念解释与出处定位</span>
                <span className="inline-flex items-center gap-1">
                  <CheckCircle2 size={14} />
                  仅基于已上传资料
                </span>
              </div>
            </div>
            {activeProject && (
              <div className="grid min-w-[260px] grid-cols-3 gap-4 border-l border-teal-soft pl-5 text-sm max-md:w-full max-md:border-l-0 max-md:pl-0">
                <Metric label="资料" value={activeProject.document_count} />
                <Metric label="题目" value={activeProject.question_count} />
                <Metric label="最近状态" value={statusLabel(activeProject.latest_status)} />
              </div>
            )}
          </div>

          {error && <div className="relative z-10 mb-4 rounded-md border border-signal bg-white px-4 py-3 text-sm text-signal">{error}</div>}

          <div className="relative z-10 grid flex-1 grid-rows-[1fr_auto] gap-5">
            <div className="trace-canvas">
              <div className="trace-rings" aria-hidden="true" />
              <div className="trace-center">
                <div className="mx-auto mb-3 grid h-10 w-10 place-items-center rounded-full bg-[#dff4f2] text-[#126c75] ring-1 ring-[#8fc9ca]">
                  <Target size={19} />
                </div>
                <p className="text-xs font-semibold text-[#28777d]">溯源请求</p>
                <p className="mt-2 text-sm leading-6 text-ink/80">
                  {question.trim() || "输入题目后，系统将从已上传资料中返回可核验的页码与片段。"}
                </p>
                <span className="mt-3 inline-flex rounded-full bg-[#eff7f4] px-3 py-1 text-xs font-medium text-[#2a7778]">
                  概念：来源定位
                </span>
              </div>

              {traceNodePreviews(documents, sourcedMatches).slice(0, 5).map((match, index) => (
                <EvidenceNode key={`${match.filename}-${index}`} match={match} index={index} />
              ))}
            </div>

            <div className="grid grid-cols-[minmax(260px,1fr)_minmax(300px,420px)] gap-5 max-2xl:grid-cols-1">
              <section data-testid="material-library" className="min-w-0 border-t border-teal-soft pt-4">
                <div className="mb-3 flex items-center justify-between gap-4">
                  <h3 className="text-base font-semibold text-[#173f43]">已上传材料</h3>
                  <label className="focus-ring inline-flex cursor-pointer items-center gap-2 rounded-md border border-dashed border-[#8ebfc0] bg-white/70 px-3 py-2 text-sm font-semibold text-[#156d75]">
                    <FileUp size={16} />
                    上传 PDF
                    <input data-testid="document-file" type="file" accept="application/pdf" onChange={uploadFile} className="sr-only" />
                  </label>
                </div>
                <div className="flex gap-3 overflow-x-auto pb-1">
                  {documents.length === 0 ? (
                    <div className="grid min-h-24 min-w-72 place-items-center rounded-md border border-dashed border-teal-soft bg-white/55 px-5 text-sm text-ink/55">
                      项目内还没有资料。
                    </div>
                  ) : (
                    documents.map((document) => <DocumentRailItem key={document.id} document={document} />)
                  )}
                </div>
              </section>

              <form onSubmit={submitQuestion} className="border-t border-teal-soft pt-4">
                <label className="text-base font-semibold text-[#173f43]" htmlFor="question">
                  手动输入题目
                </label>
                <textarea
                  id="question"
                  data-testid="question-text"
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  rows={4}
                  className="focus-ring mt-3 w-full resize-none rounded-md border border-teal-soft bg-white/90 px-4 py-3 text-sm leading-6"
                  placeholder="粘贴一道题目文本"
                />
                <button
                  disabled={busy || !activeProject}
                  className="focus-ring mt-3 inline-flex items-center gap-2 rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white disabled:opacity-55"
                >
                  {busy ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
                  查找资料依据
                </button>
              </form>
            </div>
          </div>
        </section>

        <aside
          className="flex min-h-screen flex-col border-l border-teal-soft bg-white/78 px-5 py-6 shadow-[-16px_0_40px_rgba(42,75,74,0.06)] max-xl:min-h-0 max-xl:border-l-0 max-xl:border-t"
          data-testid="evidence-preview"
        >
          <div className="mb-6 flex items-start justify-between gap-4 border-b border-teal-soft pb-5">
            <div>
              <h3 className="text-xl font-semibold text-[#173f43]">证据预览</h3>
              <p className="mt-1 text-sm text-ink/50">Evidence Preview</p>
            </div>
            <span className="rounded-md px-2 py-1 text-xs font-semibold text-[#126c75] ring-1 ring-teal-soft">来源面板</span>
          </div>

          <section className="mb-5">
            <p className="mb-2 text-xs font-semibold text-[#1f8b91]">教材</p>
            <div className="flex items-center justify-between gap-3">
              <p className="min-w-0 break-all text-lg font-semibold leading-snug text-[#173f43]">
                {sourcedMatches[0]?.filename ?? documents.find((document) => document.status === "completed")?.filename ?? "等待资料来源"}
              </p>
              <span className="shrink-0 rounded-full bg-[#edf6f4] px-3 py-1 text-sm font-semibold text-[#0d6972]">
                P. {sourcedMatches[0]?.page_no ?? "--"}
              </span>
            </div>
          </section>

          <div className="mb-4 grid grid-cols-3 gap-2 border-b border-teal-soft pb-3 text-center text-sm font-semibold text-ink/55">
            <span className="border-b-2 border-[#16727a] pb-2 text-[#126c75]">段落锚点</span>
            <span className="pb-2">页码入口</span>
            <span className="pb-2">原文片段</span>
          </div>

          <section className="min-h-[300px] flex-1">
            {!result ? (
              <EmptyEvidence>输入题目后，这里展示带文件、页码、片段和 PDF 入口的来源结果。</EmptyEvidence>
            ) : sourcedMatches.length === 0 ? (
              <EmptyEvidence>没有匹配资料。系统不会生成无来源答案。</EmptyEvidence>
            ) : (
              <div className="space-y-4">
                {sourcedMatches.map((match) => (
                  <article key={match.id} className="source-card" data-testid="source-card">
                    <div className="mb-3 flex min-w-0 items-start justify-between gap-4">
                      <div className="min-w-0">
                        <p className="break-all text-sm font-semibold text-[#173f43]">
                          {match.rank}. {match.filename} 第 {match.page_no} 页
                        </p>
                        <p className="mt-1 text-xs text-ink/55">
                          pgvector 相似度 {match.score.toFixed(4)} · {match.hit_reason}
                        </p>
                      </div>
                      <a
                        href={`${apiUrl}${match.pdf_url}`}
                        target="_blank"
                        className="focus-ring inline-flex shrink-0 items-center gap-1 rounded-md border border-teal-soft px-2 py-1 text-xs font-semibold text-[#126c75] hover:bg-[#eff7f4]"
                      >
                        <SquareArrowOutUpRight size={14} />
                        PDF
                      </a>
                    </div>
                    <p className="break-all text-sm leading-6 text-ink/78">{match.source_text}</p>
                  </article>
                ))}
              </div>
            )}
          </section>

          <div className="mt-5 grid grid-cols-[1fr_auto] items-center gap-5 border-t border-teal-soft pt-5">
            <div className="text-sm">
              <p className="font-semibold text-[#173f43]">当前请求最高匹配</p>
              <p className="mt-2 text-xs text-ink/55">pgvector 相似度 · 高相关来源片段</p>
            </div>
            <div className="grid h-24 w-24 place-items-center rounded-full border-[10px] border-[#2baba3] bg-white text-center">
              <span className="text-xl font-semibold text-[#0d6972]">{sourcedMatches[0] ? `${Math.round(sourcedMatches[0].score * 100)}%` : "--"}</span>
              <span className="sr-only">pgvector 相似度</span>
            </div>
          </div>
        </aside>
      </div>
    </main>
  );
}

function NavigationItem({
  icon,
  title,
  subtitle,
  active,
  muted
}: {
  icon: ReactNode;
  title: string;
  subtitle: string;
  active?: boolean;
  muted?: boolean;
}) {
  return (
    <div
      className={`flex items-center gap-3 rounded-md px-3 py-3 text-sm ${
        active ? "bg-[#e3f1ef] text-[#0f6972] shadow-sm ring-1 ring-[#c5dfdd]" : muted ? "text-ink/42" : "text-ink/72"
      }`}
    >
      <span className="grid h-8 w-8 shrink-0 place-items-center rounded-md border border-teal-soft bg-white/65">{icon}</span>
      <span>
        <span className="block font-semibold">{title}</span>
        <span className="block text-xs opacity-70">{subtitle}</span>
      </span>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <p className="text-xs text-ink/55">{label}</p>
      <p className="mt-1 whitespace-nowrap text-base font-semibold">{value}</p>
    </div>
  );
}

function Status({ value }: { value: string }) {
  return (
    <span data-testid="document-status" className="rounded-full border border-teal-soft bg-white px-2 py-1 text-xs font-semibold text-[#126c75]">
      {statusLabel(value)}
    </span>
  );
}

function DocumentRailItem({ document }: { document: DocumentRow }) {
  return (
    <div className="min-w-60 rounded-md border border-teal-soft bg-white/78 p-3 shadow-sm">
      <div className="flex items-start gap-3">
        <div className="grid h-14 w-11 shrink-0 place-items-center rounded bg-[#dbeeea] text-[#126c75]">
          <FileText size={20} />
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold">{document.filename}</p>
          <p className="mt-1 text-xs text-ink/55">
            PDF · {document.page_count ? `${document.page_count} 页` : "等待页数"}
          </p>
          {document.failure_reason && <p className="mt-1 line-clamp-2 text-xs text-signal">{document.failure_reason}</p>}
        </div>
      </div>
      <div className="mt-3">
        <Status value={document.status} />
      </div>
    </div>
  );
}

type NodePreview = {
  filename: string;
  page_no?: number;
  score?: number;
  state: string;
};

function EvidenceNode({ match, index }: { match: NodePreview; index: number }) {
  const positions = [
    "left-[14%] top-[16%]",
    "right-[8%] top-[20%]",
    "right-[6%] bottom-[16%]",
    "left-[12%] bottom-[18%]",
    "left-[44%] bottom-[3%]"
  ];
  const colors = ["#126c75", "#5d7d63", "#168889", "#907a54", "#47869b"];
  return (
    <div className={`evidence-node ${positions[index] ?? positions[0]}`}>
      <div className="node-orbit" style={{ borderColor: colors[index] }} />
      <div className="node-body">
        <span className="rounded-full bg-[#0f6972] px-2 py-1 text-xs font-semibold text-white">P. {match.page_no || "--"}</span>
        <p className="mt-2 line-clamp-2 text-xs font-semibold text-[#173f43]">{match.filename}</p>
        <p className="mt-1 text-xs text-[#2b777a]">{match.score ? `相似度 ${Math.round(match.score * 100)}%` : match.state}</p>
      </div>
    </div>
  );
}

function EmptyEvidence({ children }: { children: ReactNode }) {
  return (
    <div className="grid min-h-[360px] place-items-center rounded-md border border-dashed border-teal-soft bg-[#fbfaf6] px-8 text-center text-sm leading-6 text-ink/58">
      <p>{children}</p>
    </div>
  );
}

function traceNodePreviews(documents: DocumentRow[], matches: Match[]): NodePreview[] {
  if (matches.length > 0) {
    return matches.map((match) => ({
      filename: match.filename,
      page_no: match.page_no,
      score: match.score,
      state: match.hit_reason
    }));
  }
  const uploaded = documents.slice(0, 5).map((document) => ({
    filename: document.filename,
    state: statusLabel(document.status)
  }));
  if (uploaded.length > 0) {
    return uploaded;
  }
  return [
    { filename: "等待上传资料", state: "未检索" },
    { filename: "等待题目输入", state: "未检索" },
    { filename: "等待来源结果", state: "未检索" }
  ];
}

function statusLabel(value: string) {
  const labels: Record<string, string> = {
    none: "无资料",
    uploaded: "已上传",
    processing: "处理中",
    completed: "完成",
    failed: "失败",
    unsupported: "不支持"
  };
  return labels[value] ?? value;
}

function hasSource(match: Match) {
  return Boolean(match.filename && match.page_no && match.source_text.trim() && match.pdf_url);
}
