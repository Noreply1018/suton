"use client";

import { ChangeEvent, FormEvent, ReactNode, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertCircle,
  ArrowUpRight,
  BookOpen,
  CheckCircle2,
  FileText,
  FileUp,
  FolderOpen,
  Library,
  Loader2,
  MoreHorizontal,
  Pencil,
  Plus,
  Search,
  ShieldCheck,
  Trash2,
  X
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
  document_filename: string;
  pdf_url: string;
};

type QuestionResult = {
  id: number;
  text: string;
  status: string;
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
  const [projectDialog, setProjectDialog] = useState<"create" | "rename" | "delete" | null>(null);
  const [projectFormName, setProjectFormName] = useState("");
  const [projectDialogError, setProjectDialogError] = useState("");
  const [projectMenuOpen, setProjectMenuOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<QuestionResult | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const activeProjectIdRef = useRef<number | null>(null);
  const documentFileInputRef = useRef<HTMLInputElement>(null);
  const refreshSeqRef = useRef(0);

  const activeProject = useMemo(
    () => projects.find((project) => project.id === activeProjectId) ?? null,
    [activeProjectId, projects]
  );
  const sourcedMatches = useMemo(() => result?.matches.filter(hasSource) ?? [], [result]);
  const completedDocuments = documents.filter((document) => document.status === "completed").length;

  useEffect(() => {
    activeProjectIdRef.current = activeProjectId;
  }, [activeProjectId]);

  async function refresh(preferredProjectId?: number) {
    const requestSeq = ++refreshSeqRef.current;
    const nextProjects = await request<Project[]>("/projects");
    if (requestSeq !== refreshSeqRef.current) return;

    setProjects(nextProjects);
    const preferredExists = preferredProjectId ? nextProjects.some((project) => project.id === preferredProjectId) : false;
    const currentProjectId = activeProjectIdRef.current;
    const currentExists = currentProjectId ? nextProjects.some((project) => project.id === currentProjectId) : false;
    const nextActive = (preferredExists ? preferredProjectId : currentExists ? currentProjectId : nextProjects[0]?.id) ?? null;
    setActiveProjectId(nextActive);
    activeProjectIdRef.current = nextActive;
    if (nextActive) {
      const nextDocuments = await request<DocumentRow[]>(`/projects/${nextActive}/documents`);
      if (requestSeq === refreshSeqRef.current && activeProjectIdRef.current === nextActive) {
        setDocuments(nextDocuments);
      }
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!activeProjectId) return;
    const timer = window.setInterval(() => {
      refresh(activeProjectId).catch(() => undefined);
    }, 5000);
    return () => window.clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeProjectId]);

  async function selectProject(projectId: number) {
    const requestSeq = ++refreshSeqRef.current;
    setActiveProjectId(projectId);
    activeProjectIdRef.current = projectId;
    setResult(null);
    setError("");
    const nextDocuments = await request<DocumentRow[]>(`/projects/${projectId}/documents`);
    if (requestSeq === refreshSeqRef.current && activeProjectIdRef.current === projectId) {
      setDocuments(nextDocuments);
    }
  }

  function openCreateProjectDialog() {
    setProjectFormName("");
    setProjectDialogError("");
    setProjectMenuOpen(false);
    setProjectDialog("create");
  }

  function openRenameProjectDialog() {
    if (!activeProject) return;
    setProjectFormName(activeProject.name);
    setProjectDialogError("");
    setProjectMenuOpen(false);
    setProjectDialog("rename");
  }

  function openDeleteProjectDialog() {
    if (!activeProject) return;
    setProjectDialogError("");
    setProjectMenuOpen(false);
    setProjectDialog("delete");
  }

  function closeProjectDialog() {
    if (busy) return;
    setProjectDialog(null);
    setProjectDialogError("");
  }

  function validateProjectName(name: string) {
    const trimmedName = name.trim();
    if (!trimmedName) return "项目名称不能为空";
    if (trimmedName.length > 80) return "项目名称不能超过 80 个字符";
    return "";
  }

  async function createProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const validationError = validateProjectName(projectFormName);
    if (validationError) {
      setProjectDialogError(validationError);
      return;
    }
    setProjectDialogError("");
    setBusy(true);
    try {
      const project = await request<Project>("/projects", {
        method: "POST",
        body: JSON.stringify({ name: projectFormName })
      });
      setActiveProjectId(project.id);
      activeProjectIdRef.current = project.id;
      setResult(null);
      await refresh(project.id);
      setProjectDialog(null);
      setProjectFormName("");
    } catch (err) {
      setProjectDialogError(err instanceof Error ? err.message : "创建项目失败");
    } finally {
      setBusy(false);
    }
  }

  async function renameProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!activeProject) return;
    const validationError = validateProjectName(projectFormName);
    if (validationError) {
      setProjectDialogError(validationError);
      return;
    }
    setProjectDialogError("");
    setBusy(true);
    const projectId = activeProject.id;
    try {
      const project = await request<Project>(`/projects/${projectId}`, {
        method: "PATCH",
        body: JSON.stringify({ name: projectFormName })
      });
      setActiveProjectId(project.id);
      activeProjectIdRef.current = project.id;
      await refresh(project.id);
      setProjectDialog(null);
    } catch (err) {
      setProjectDialogError(err instanceof Error ? err.message : "重命名项目失败");
    } finally {
      setBusy(false);
    }
  }

  async function deleteProject() {
    if (!activeProject) return;
    setProjectDialogError("");
    setBusy(true);
    try {
      await request(`/projects/${activeProject.id}`, { method: "DELETE" });
      setResult(null);
      await refresh();
      setProjectDialog(null);
    } catch (err) {
      setProjectDialogError(err instanceof Error ? err.message : "删除项目失败");
    } finally {
      setBusy(false);
    }
  }

  async function uploadFile(event: ChangeEvent<HTMLInputElement>) {
    if (!activeProject) {
      setError("请先创建项目");
      event.target.value = "";
      return;
    }
    if (!event.target.files?.[0]) return;
    setError("");
    const formData = new FormData();
    formData.append("file", event.target.files[0]);
    setBusy(true);
    const projectId = activeProject.id;
    try {
      await request(`/projects/${projectId}/documents`, { method: "POST", body: formData });
      if (activeProjectIdRef.current === projectId) {
        await refresh(projectId);
      }
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
    const projectId = activeProject.id;
    try {
      const nextResult = await request<QuestionResult>(`/projects/${projectId}/questions`, {
        method: "POST",
        body: JSON.stringify({ text: question })
      });
      if (activeProjectIdRef.current === projectId) {
        setResult(nextResult);
        await refresh(projectId);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "检索失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="paper-shell min-h-screen text-ink" data-testid="app-shell">
      <div className="grid min-h-screen grid-cols-[260px_minmax(0,1fr)_390px] max-2xl:grid-cols-[240px_minmax(0,1fr)_360px] max-xl:grid-cols-1">
        <aside className="paper-sidebar flex min-h-screen flex-col px-5 py-6 max-xl:min-h-0" data-testid="sidebar-nav">
          <div className="mb-7">
            <div className="mb-2 flex items-center gap-3">
              <div className="grid h-11 w-11 place-items-center rounded-md bg-[#d8eadb] text-[#204f3a] ring-1 ring-[#b5d1bd]">
                <BookOpen size={21} />
              </div>
              <div>
                <h1 className="text-2xl font-semibold tracking-normal text-[#204832]">Suton</h1>
              <p className="text-xs text-[#526050]">资料出处核验台</p>
              </div>
            </div>
            <div className="mt-5 grid grid-cols-3 gap-2 border-y border-[#d8dfd0] py-4 text-sm">
              <Metric label="资料" value={activeProject?.document_count ?? 0} />
              <Metric label="题目" value={activeProject?.question_count ?? 0} />
              <Metric label="完成" value={completedDocuments} />
            </div>
          </div>

          <div className="mb-5">
            <button
              type="button"
              onClick={openCreateProjectDialog}
              className="focus-ring inline-flex w-full items-center justify-center gap-2 rounded-md bg-[#315f43] px-3 py-2 text-sm font-semibold text-white transition hover:bg-[#264b35]"
            >
              <Plus size={16} />
              新建项目
            </button>
          </div>

          <div className="min-h-0 flex-1 space-y-2 overflow-auto">
            {projects.length === 0 ? (
              <p className="border-y border-[#d8dfd0] py-5 text-sm leading-6 text-[#526050]">创建一个项目后开始上传资料。</p>
            ) : (
              projects.map((project) => (
                <button
                  key={project.id}
                  onClick={() => {
                    selectProject(project.id).catch((err: Error) => setError(err.message));
                  }}
                  className={`focus-ring w-full rounded-md px-3 py-3 text-left text-sm transition ${
                    activeProject?.id === project.id
                      ? "bg-[#f8fbf3] text-[#203a2b] shadow-sm ring-1 ring-[#bfd3bf]"
                      : "text-[#445346] hover:bg-[#f8fbf3]"
                  }`}
                >
                  <span className="block truncate font-semibold">{project.name}</span>
                  <span className="mt-1 block text-xs text-[#526050]">
                    {project.document_count} 份资料 · {project.question_count} 道题 · {statusLabel(project.latest_status)}
                  </span>
                </button>
              ))
            )}
          </div>

          <div className="mt-6 rounded-md border border-[#c8d9c8] bg-[#edf6e9] p-4 text-sm text-[#31583e]">
            <div className="mb-2 flex items-center gap-2 font-semibold">
              <ShieldCheck size={17} />
              只展示有来源的结果
            </div>
            <p className="text-xs leading-5 text-[#485d4b]">不生成无来源答案，只返回资料文件、页码和原文片段。</p>
          </div>
        </aside>

        <section className="min-w-0 px-8 py-7 max-md:px-5" data-testid="trace-workspace">
          <div className="mb-6 flex items-start justify-between gap-5 max-md:flex-col">
            <div className="min-w-0">
              <p className="mb-2 text-sm font-semibold text-[#496f45]">当前项目</p>
              <div className="flex min-w-0 items-center gap-2">
                <h2 className="break-words text-3xl font-semibold tracking-normal text-[#1f3428]">
                  {activeProject?.name ?? "尚未创建项目"}
                </h2>
                {activeProject && (
                  <div className="relative shrink-0">
                    <button
                      type="button"
                      aria-label="项目操作"
                      aria-expanded={projectMenuOpen}
                      onClick={() => setProjectMenuOpen((open) => !open)}
                      className="focus-ring grid h-9 w-9 place-items-center rounded-md border border-[#c6d6c5] bg-[#f8fbf4] text-[#315f43] hover:bg-[#edf6e9]"
                    >
                      <MoreHorizontal size={18} />
                    </button>
                    {projectMenuOpen && (
                      <div className="absolute left-0 top-11 z-20 w-36 rounded-md border border-[#c8d8c7] bg-[#fbfcf8] p-1 shadow-lg">
                        <button
                          type="button"
                          onClick={openRenameProjectDialog}
                          className="focus-ring flex w-full items-center gap-2 rounded px-2 py-2 text-left text-sm text-[#273d2f] hover:bg-[#edf6e9]"
                        >
                          <Pencil size={15} />
                          重命名
                        </button>
                        <button
                          type="button"
                          onClick={openDeleteProjectDialog}
                          className="focus-ring flex w-full items-center gap-2 rounded px-2 py-2 text-left text-sm text-[#9d4d2f] hover:bg-[#fff1ec]"
                        >
                          <Trash2 size={15} />
                          删除项目
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
            <div className="flex shrink-0 items-center gap-2 rounded-md border border-[#d0dccd] bg-[#f9fbf5] px-3 py-2 text-sm text-[#425542]">
              <CheckCircle2 size={16} />
              本地来源闭环
            </div>
          </div>

          {error && (
            <div className="mb-5 flex items-start gap-2 rounded-md border border-[#c98972] bg-[#fff8f4] px-4 py-3 text-sm text-[#9d4d2f]">
              <AlertCircle size={16} className="mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div className="grid gap-6">
            <section className="paper-panel" data-testid="material-library">
              <div className="mb-4 flex items-center justify-between gap-4 max-sm:flex-col max-sm:items-start">
                <div>
                  <div className="flex items-center gap-2 text-[#203a2b]">
                    <Library size={18} />
                    <h3 className="text-lg font-semibold">资料库</h3>
                  </div>
                  <p className="mt-1 text-sm text-[#4f5d50]">上传带文字层的 PDF，系统解析页面文本并建立 pgvector 索引。</p>
                </div>
                <button
                  type="button"
                  aria-describedby="document-upload-note"
                  onClick={() => {
                    if (activeProject) {
                      documentFileInputRef.current?.click();
                    } else {
                      openCreateProjectDialog();
                    }
                  }}
                  className={`focus-ring inline-flex items-center gap-2 rounded-md border border-[#b8cdb8] px-3 py-2 text-sm font-semibold text-[#244c35] transition ${
                    activeProject ? "bg-[#e4f0df] hover:bg-[#d9ead4]" : "bg-[#e4f0df] hover:bg-[#d9ead4]"
                  }`}
                >
                  <FileUp size={16} />
                  {documents.length === 0 ? "添加第一份课程资料" : "上传 PDF"}
                  <input
                    ref={documentFileInputRef}
                    data-testid="document-file"
                    type="file"
                    accept="application/pdf"
                    disabled={!activeProject}
                    onChange={uploadFile}
                    tabIndex={-1}
                    className="hidden"
                  />
                </button>
              </div>
              <p id="document-upload-note" className="sr-only">
                请先创建项目，再上传 PDF 资料。
              </p>

              <div className="divide-y divide-[#dce4d7] border-y border-[#dce4d7]">
                {!activeProject ? (
                  <FirstEmptyProject />
                ) : documents.length === 0 ? (
                  <p className="py-8 text-sm text-[#516050]">项目内还没有资料。</p>
                ) : (
                  documents.map((document) => <DocumentRowView key={document.id} document={document} />)
                )}
              </div>
            </section>

            <section className="paper-panel">
              <div className="mb-4 flex items-center gap-2 text-[#203a2b]">
                <Search size={18} />
                <h3 className="text-lg font-semibold">溯源请求</h3>
              </div>
              <form onSubmit={submitQuestion}>
                <label className="sr-only" htmlFor="question">
                  手动输入题目
                </label>
                <textarea
                  id="question"
                  data-testid="question-text"
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  rows={7}
                  className="focus-ring w-full resize-none rounded-md border border-[#c9d7c8] bg-[#fbfcf8] px-4 py-3 text-sm leading-6 text-[#26382d]"
                  placeholder="粘贴一道题目文本"
                />
                <div className="mt-4 flex items-center justify-between gap-4 max-sm:flex-col max-sm:items-start">
                  <p className="text-sm text-[#4f5d50]">提交后仅返回带文件、页码和片段的资料依据。</p>
                  <button
                    disabled={busy || !activeProject}
                    className="focus-ring inline-flex items-center gap-2 rounded-md bg-[#315f43] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[#264b35] disabled:opacity-55"
                  >
                    {busy ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
                    查找资料依据
                  </button>
                </div>
              </form>
            </section>
          </div>
        </section>

        <aside className="paper-inspector min-h-screen px-5 py-7 max-xl:min-h-0" data-testid="evidence-preview">
          <div className="mb-5">
            <div className="flex items-center gap-2 text-[#203a2b]">
              <FolderOpen size={18} />
              <h3 className="text-xl font-semibold">资料依据</h3>
            </div>
            <p className="mt-1 text-sm text-[#4f5d50]">Source Results</p>
          </div>

          {!result ? (
            <EmptyResults>输入题目后，这里展示带文件、页码、片段和 PDF 入口的来源结果。</EmptyResults>
          ) : sourcedMatches.length === 0 ? (
            <EmptyResults>没有匹配资料。系统不会生成无来源答案。</EmptyResults>
          ) : (
            <div className="space-y-4">
              {sourcedMatches.map((match) => (
                <article key={match.id} className="source-card" data-testid="source-card">
                  <div className="mb-3 flex min-w-0 items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="break-all text-sm font-semibold text-[#203a2b]">
                        {match.rank}. {match.document_filename} 第 {match.page_no} 页
                      </p>
                      <p className="mt-1 text-xs text-[#5e6d5d]">
                        pgvector 相似度 {match.score.toFixed(4)} · {match.hit_reason}
                      </p>
                    </div>
                    <a
                      href={`${apiUrl}${match.pdf_url}`}
                      target="_blank"
                      className="focus-ring inline-flex shrink-0 items-center gap-1 rounded-md border border-[#b8cdb8] bg-[#f8fbf4] px-2 py-1 text-xs font-semibold text-[#315f43] hover:bg-[#edf6e9]"
                    >
                      <ArrowUpRight size={14} />
                      PDF
                    </a>
                  </div>
                  <p className="break-all text-sm leading-6 text-[#435244]">{match.source_text}</p>
                </article>
              ))}
            </div>
          )}
        </aside>
      </div>
      {projectDialog === "create" && (
        <ProjectNameDialog
          title="新建项目"
          submitLabel="创建"
          name={projectFormName}
          error={projectDialogError}
          busy={busy}
          onNameChange={setProjectFormName}
          onClose={closeProjectDialog}
          onSubmit={createProject}
        />
      )}
      {projectDialog === "rename" && (
        <ProjectNameDialog
          title="重命名项目"
          submitLabel="保存"
          name={projectFormName}
          error={projectDialogError}
          busy={busy}
          onNameChange={setProjectFormName}
          onClose={closeProjectDialog}
          onSubmit={renameProject}
        />
      )}
      {projectDialog === "delete" && activeProject && (
        <ProjectDeleteDialog project={activeProject} error={projectDialogError} busy={busy} onClose={closeProjectDialog} onConfirm={deleteProject} />
      )}
    </main>
  );
}

function ProjectNameDialog({
  title,
  submitLabel,
  name,
  error,
  busy,
  onNameChange,
  onClose,
  onSubmit
}: {
  title: string;
  submitLabel: string;
  name: string;
  error: string;
  busy: boolean;
  onNameChange: (name: string) => void;
  onClose: () => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <DialogFrame title={title} onClose={onClose}>
      <form onSubmit={onSubmit} className="space-y-4">
        <div>
          <label className="mb-2 block text-sm font-semibold text-[#273d2f]" htmlFor="project-dialog-name">
            项目名称
          </label>
          <input
            id="project-dialog-name"
            autoFocus
            value={name}
            onChange={(event) => onNameChange(event.target.value)}
            placeholder="例如：高性能计算期末"
            className="focus-ring w-full rounded-md border border-[#cbd8c9] bg-[#fbfcf8] px-3 py-2 text-sm"
          />
          {error && <p className="mt-2 text-sm text-[#9d4d2f]">{error}</p>}
        </div>
        <div className="flex justify-end gap-2">
          <button
            type="button"
            disabled={busy}
            onClick={onClose}
            className="focus-ring rounded-md border border-[#c6d6c5] bg-[#fbfcf8] px-3 py-2 text-sm font-semibold text-[#315f43] disabled:opacity-55"
          >
            取消
          </button>
          <button
            disabled={busy}
            className="focus-ring inline-flex items-center gap-2 rounded-md bg-[#315f43] px-3 py-2 text-sm font-semibold text-white disabled:opacity-55"
          >
            {busy && <Loader2 size={16} className="animate-spin" />}
            {submitLabel}
          </button>
        </div>
      </form>
    </DialogFrame>
  );
}

function ProjectDeleteDialog({
  project,
  error,
  busy,
  onClose,
  onConfirm
}: {
  project: Project;
  error: string;
  busy: boolean;
  onClose: () => void;
  onConfirm: () => void;
}) {
  return (
    <DialogFrame title="删除项目" onClose={onClose}>
      <div className="space-y-3 text-sm leading-6 text-[#3f5142]">
        <p className="font-semibold text-[#1f3428]">删除项目及其全部资料</p>
        <p>将删除项目、全部资料、题目和来源结果。</p>
        <p>
          项目：{project.name} · 资料 {project.document_count} 份 · 题目 {project.question_count} 道
        </p>
        {error && <p className="text-[#9d4d2f]">{error}</p>}
      </div>
      <div className="mt-5 flex justify-end gap-2">
        <button
          type="button"
          disabled={busy}
          onClick={onClose}
          className="focus-ring rounded-md border border-[#c6d6c5] bg-[#fbfcf8] px-3 py-2 text-sm font-semibold text-[#315f43] disabled:opacity-55"
        >
          取消
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={onConfirm}
          className="focus-ring inline-flex items-center gap-2 rounded-md bg-[#9d4d2f] px-3 py-2 text-sm font-semibold text-white disabled:opacity-55"
        >
          {busy && <Loader2 size={16} className="animate-spin" />}
          确认删除
        </button>
      </div>
    </DialogFrame>
  );
}

function DialogFrame({ title, children, onClose }: { title: string; children: ReactNode; onClose: () => void }) {
  return (
    <div
      role="presentation"
      onKeyDown={(event) => {
        if (event.key === "Escape") onClose();
      }}
      className="fixed inset-0 z-50 grid place-items-center bg-[#17251d]/35 px-4"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="project-dialog-title"
        className="w-full max-w-[440px] rounded-md border border-[#c8d8c7] bg-[#fbfcf8] p-5 shadow-xl"
      >
        <div className="mb-4 flex items-center justify-between gap-4">
          <h2 id="project-dialog-title" className="text-xl font-semibold text-[#1f3428]">
            {title}
          </h2>
          <button
            type="button"
            aria-label="关闭"
            onClick={onClose}
            className="focus-ring grid h-8 w-8 place-items-center rounded-md border border-[#c6d6c5] text-[#315f43] hover:bg-[#edf6e9]"
          >
            <X size={16} />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <p className="text-xs text-[#526050]">{label}</p>
      <p className="mt-1 truncate text-sm font-semibold text-[#24382c]">{value}</p>
    </div>
  );
}

function DocumentRowView({ document }: { document: DocumentRow }) {
  return (
    <div className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-start gap-3 py-4">
      <div className="mt-0.5 grid h-9 w-9 place-items-center rounded-md bg-[#e5efe0] text-[#315f43]">
        <FileText size={18} />
      </div>
      <div className="min-w-0">
        <p className="truncate text-sm font-semibold text-[#26382d]">{document.filename}</p>
        <p className="mt-1 text-xs text-[#516050]">
          {document.page_count ? `${document.page_count} 页` : "等待页数"}
          {document.failure_reason ? ` · ${document.failure_reason}` : ""}
        </p>
      </div>
      <Status value={document.status} />
    </div>
  );
}

function FirstEmptyProject() {
  return (
    <div data-testid="v020-first-empty-project" className="py-8">
      <div className="max-w-[520px]">
        <p className="text-lg font-semibold text-[#203a2b]">添加第一份课程资料</p>
        <p className="mt-2 text-sm leading-6 text-[#516050]">
          先创建一个项目名称，再上传带文字层的 PDF。这里会显示页数、文字层质量和处理状态。
        </p>
      </div>
    </div>
  );
}

function Status({ value }: { value: string }) {
  return (
    <span data-testid="document-status" className="rounded-full border border-[#c5d6c2] bg-[#f8fbf4] px-2 py-1 text-xs font-semibold text-[#315f43]">
      {statusLabel(value)}
    </span>
  );
}

function EmptyResults({ children }: { children: ReactNode }) {
  return (
    <div className="grid min-h-[360px] place-items-center border-y border-[#dce4d7] px-6 text-center text-sm leading-6 text-[#4f5d50]">
      <p>{children}</p>
    </div>
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
  return Boolean(match.document_filename && match.page_no && match.source_text.trim() && match.pdf_url);
}
