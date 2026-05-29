"use client";

import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from "react";
import { BookOpen, FileUp, Loader2, Plus, Search, SquareArrowOutUpRight } from "lucide-react";

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

  async function refresh() {
    const nextProjects = await request<Project[]>("/projects");
    setProjects(nextProjects);
    const nextActive = activeProjectId ?? nextProjects[0]?.id ?? null;
    setActiveProjectId(nextActive);
    if (nextActive) {
      setDocuments(await request<DocumentRow[]>(`/projects/${nextActive}/documents`));
    } else {
      setDocuments([]);
    }
  }

  useEffect(() => {
    refresh().catch((err: Error) => setError(err.message));
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
      await refresh();
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
    <main className="min-h-screen bg-paper text-ink">
      <div className="grid min-h-screen grid-cols-[280px_1fr] max-lg:grid-cols-1">
        <aside className="border-r border-line bg-[#ebe5d8] p-5 max-lg:border-b max-lg:border-r-0">
          <div className="mb-8 flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded bg-ink text-paper">
              <BookOpen size={20} />
            </div>
            <div>
              <h1 className="text-xl font-semibold">Suton</h1>
              <p className="text-sm text-ink/65">v0.1.0 资料溯源</p>
            </div>
          </div>

          <form onSubmit={createProject} className="mb-6 space-y-3">
            <label className="text-sm font-medium" htmlFor="project-name">
              新建项目
            </label>
            <input
              id="project-name"
              value={projectName}
              onChange={(event) => setProjectName(event.target.value)}
              className="focus-ring w-full rounded border border-line bg-paper px-3 py-2 text-sm"
            />
            <button
              disabled={busy}
              className="focus-ring flex w-full items-center justify-center gap-2 rounded bg-accent px-3 py-2 text-sm font-medium text-white disabled:opacity-55"
            >
              <Plus size={16} />
              创建项目
            </button>
          </form>

          <nav className="space-y-2">
            {projects.map((project) => (
              <button
                key={project.id}
                onClick={() => setActiveProjectId(project.id)}
                className={`focus-ring w-full rounded px-3 py-3 text-left text-sm transition ${
                  activeProject?.id === project.id ? "bg-ink text-paper" : "hover:bg-paper"
                }`}
              >
                <span className="block font-medium">{project.name}</span>
                <span className="mt-1 block text-xs opacity-70">
                  {project.document_count} 份资料 · {project.question_count} 道题
                </span>
              </button>
            ))}
          </nav>
        </aside>

        <section className="p-8 max-lg:p-5">
          <div className="mb-6 flex items-start justify-between gap-6 max-md:flex-col">
            <div>
              <p className="text-sm text-ink/60">当前项目</p>
              <h2 className="mt-1 text-3xl font-semibold tracking-normal">{activeProject?.name ?? "尚未创建项目"}</h2>
            </div>
            {activeProject && (
              <div className="grid grid-cols-3 gap-6 border-l border-line pl-6 text-sm max-md:w-full max-md:border-l-0 max-md:pl-0">
                <Metric label="资料" value={activeProject.document_count} />
                <Metric label="题目" value={activeProject.question_count} />
                <Metric label="最近状态" value={statusLabel(activeProject.latest_status)} />
              </div>
            )}
          </div>

          {error && <div className="mb-5 rounded border border-signal bg-white px-4 py-3 text-sm text-signal">{error}</div>}

          <div className="grid grid-cols-[minmax(300px,420px)_1fr] gap-8 max-xl:grid-cols-1">
            <section className="space-y-8">
              <div>
                <div className="mb-3 flex items-center justify-between">
                  <h3 className="text-lg font-semibold">资料库</h3>
                  <label className="focus-ring inline-flex cursor-pointer items-center gap-2 rounded bg-ink px-3 py-2 text-sm font-medium text-paper">
                    <FileUp size={16} />
                    上传 PDF
                    <input data-testid="document-file" type="file" accept="application/pdf" onChange={uploadFile} className="sr-only" />
                  </label>
                </div>
                <div className="divide-y divide-line border-y border-line">
                  {documents.length === 0 ? (
                    <p className="py-8 text-sm text-ink/60">项目内还没有资料。</p>
                  ) : (
                    documents.map((document) => (
                      <div key={document.id} className="py-4">
                        <div className="flex items-center justify-between gap-4">
                          <p className="truncate text-sm font-medium">{document.filename}</p>
                          <Status value={document.status} />
                        </div>
                        <p className="mt-1 text-xs text-ink/60">
                          {document.page_count ? `${document.page_count} 页` : "等待页数"}{" "}
                          {document.failure_reason ? `· ${document.failure_reason}` : ""}
                        </p>
                      </div>
                    ))
                  )}
                </div>
              </div>

              <form onSubmit={submitQuestion} className="space-y-3">
                <label className="text-lg font-semibold" htmlFor="question">
                  手动输入题目
                </label>
                <textarea
                  id="question"
                  data-testid="question-text"
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  rows={8}
                  className="focus-ring w-full resize-none rounded border border-line bg-white px-4 py-3 text-sm leading-6"
                  placeholder="粘贴一道题目文本"
                />
                <button
                  disabled={busy || !activeProject}
                  className="focus-ring inline-flex items-center gap-2 rounded bg-accent px-4 py-2 text-sm font-medium text-white disabled:opacity-55"
                >
                  {busy ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
                  查找资料依据
                </button>
              </form>
            </section>

            <section>
              <div className="mb-3 flex items-center justify-between border-b border-line pb-3">
                <h3 className="text-lg font-semibold">资料依据</h3>
                {result && <span className="text-sm text-ink/60">{sourcedMatches.length} 条结果</span>}
              </div>
              {!result ? (
                <div className="grid min-h-[360px] place-items-center border-b border-line text-center text-sm text-ink/60">
                  <p>输入题目后，这里展示带文件、页码、片段和 PDF 入口的来源结果。</p>
                </div>
              ) : sourcedMatches.length === 0 ? (
                <div className="grid min-h-[360px] place-items-center border-b border-line text-center text-sm text-ink/60">
                  <p>没有匹配资料。系统不会生成无来源答案。</p>
                </div>
              ) : (
                <div className="divide-y divide-line border-b border-line">
                  {sourcedMatches.map((match) => (
                    <article key={match.id} className="py-5">
                      <div className="mb-2 flex items-start justify-between gap-4">
                        <div>
                          <p className="text-sm font-semibold">
                            {match.rank}. {match.filename} 第 {match.page_no} 页
                          </p>
                          <p className="mt-1 text-xs text-ink/60">
                            pgvector 相似度 {match.score.toFixed(4)} · {match.hit_reason}
                          </p>
                        </div>
                        <a
                          href={`${apiUrl}${match.pdf_url}`}
                          target="_blank"
                          className="focus-ring inline-flex shrink-0 items-center gap-1 rounded border border-line px-2 py-1 text-xs font-medium hover:bg-white"
                        >
                          <SquareArrowOutUpRight size={14} />
                          PDF
                        </a>
                      </div>
                      <p className="text-sm leading-6 text-ink/80">{match.source_text}</p>
                    </article>
                  ))}
                </div>
              )}
            </section>
          </div>
        </section>
      </div>
    </main>
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
    <span data-testid="document-status" className="rounded border border-line bg-white px-2 py-1 text-xs font-medium text-ink/75">
      {statusLabel(value)}
    </span>
  );
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
