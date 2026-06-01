"use client";

import { ChangeEvent, FormEvent, ReactNode, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  ArrowUpRight,
  BookOpen,
  ChevronLeft,
  ChevronRight,
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
  content_type: string;
  page_count: number | null;
  extractable_page_count: number;
  chunk_count: number;
  text_quality: string;
  text_quality_label: string;
  searchable: boolean;
  status: string;
  processing_stage: string;
  failed_stage: string | null;
  failure_code: string | null;
  failure_reason: string | null;
  created_at: string;
  processed_at: string | null;
  updated_at: string;
};

type Match = {
  id: number;
  question_id: number;
  document_id: number;
  rank: number;
  score: number;
  confidence_level: string;
  confidence_label: string;
  hit_reason: string;
  source_text: string;
  context_before: string;
  context_after: string;
  page_no: number;
  chunk_id: number;
  document_filename: string;
  pdf_url: string;
};

type QuestionResult = {
  id: number;
  text: string;
  status: string;
  matches: Match[];
};

type SourceDetail = Match & {
  filename: string;
  page_count: number;
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
  const [documentToDelete, setDocumentToDelete] = useState<DocumentRow | null>(null);
  const [documentDialogError, setDocumentDialogError] = useState("");
  const [selectedDocument, setSelectedDocument] = useState<DocumentRow | null>(null);
  const [scopeMode, setScopeMode] = useState<"all" | "selected">("all");
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<number[]>([]);
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<QuestionResult | null>(null);
  const [sourceDetail, setSourceDetail] = useState<SourceDetail | null>(null);
  const [sourceDetailError, setSourceDetailError] = useState("");
  const [currentSourcePage, setCurrentSourcePage] = useState<number | null>(null);
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
  const selectedScopeIds = useMemo(
    () => documents.filter((document) => selectedDocumentIds.includes(document.id)).map((document) => document.id),
    [documents, selectedDocumentIds]
  );
  const questionSubmitDisabled = busy || !activeProject || (scopeMode === "selected" && selectedScopeIds.length === 0);

  useEffect(() => {
    activeProjectIdRef.current = activeProjectId;
  }, [activeProjectId]);

  useEffect(() => {
    if (!selectedDocument) return;
    const currentDocument = documents.find((document) => document.id === selectedDocument.id);
    setSelectedDocument(currentDocument ?? null);
  }, [documents, selectedDocument]);

  useEffect(() => {
    setSourceDetail(null);
    setSourceDetailError("");
    setCurrentSourcePage(null);
  }, [result?.id]);

  useEffect(() => {
    setSelectedDocumentIds((current) =>
      documents.filter((document) => document.searchable && current.includes(document.id)).map((document) => document.id)
    );
  }, [documents]);

  useEffect(() => {
    setScopeMode("all");
    setSelectedDocumentIds([]);
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
    setSourceDetail(null);
    setSourceDetailError("");
    setCurrentSourcePage(null);
    setSelectedDocument(null);
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
      setSelectedDocument(null);
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
      setSelectedDocument(null);
      await refresh();
      setProjectDialog(null);
    } catch (err) {
      setProjectDialogError(err instanceof Error ? err.message : "删除项目失败");
    } finally {
      setBusy(false);
    }
  }

  function openDeleteDocumentDialog(document: DocumentRow) {
    setDocumentToDelete(document);
    setDocumentDialogError("");
  }

  function closeDeleteDocumentDialog() {
    if (busy) return;
    setDocumentToDelete(null);
    setDocumentDialogError("");
  }

  async function deleteDocument() {
    if (!documentToDelete || !activeProject) return;
    setDocumentDialogError("");
    setBusy(true);
    const projectId = activeProject.id;
    try {
      await request(`/documents/${documentToDelete.id}`, { method: "DELETE" });
      await refresh(projectId);
      setDocumentToDelete(null);
      setSelectedDocument(null);
    } catch (err) {
      setDocumentDialogError(err instanceof Error ? err.message : "删除资料失败");
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
    const documentIds = scopeMode === "all" ? null : selectedScopeIds;
    if (scopeMode === "selected" && selectedScopeIds.length === 0) return;
    setError("");
    setResult(null);
    setSourceDetail(null);
    setSourceDetailError("");
    setCurrentSourcePage(null);
    setBusy(true);
    const projectId = activeProject.id;
    try {
      const nextResult = await request<QuestionResult>(`/projects/${projectId}/questions`, {
        method: "POST",
        body: JSON.stringify({ text: question, document_ids: documentIds })
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

  function toggleScopeDocument(document: DocumentRow) {
    if (!document.searchable) return;
    setSelectedDocumentIds((current) =>
      current.includes(document.id) ? current.filter((documentId) => documentId !== document.id) : [...current, document.id]
    );
  }

  async function openSourceDetail(match: Match) {
    if (!result) return;
    setSourceDetailError("");
    try {
      const detail = await request<Match & { filename: string }>(`/questions/${result.id}/matches/${match.id}`);
      const cachedDocument = documents.find((document) => document.id === detail.document_id);
      const document = cachedDocument ?? (await request<DocumentRow>(`/documents/${detail.document_id}`));
      if (document.page_count === null) {
        throw new Error("资料页数缺失");
      }
      setSourceDetail({ ...detail, page_count: document.page_count });
      setCurrentSourcePage(detail.page_no);
    } catch (err) {
      setSourceDetail(null);
      setCurrentSourcePage(null);
      setSourceDetailError(err instanceof Error ? err.message : "来源详情打开失败");
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
                  documents.map((document) => (
                    <DocumentRowView
                      key={document.id}
                      document={document}
                      selected={selectedDocument?.id === document.id}
                      onSelect={setSelectedDocument}
                      onDelete={openDeleteDocumentDialog}
                    />
                  ))
                )}
              </div>
              {selectedDocument && <DocumentDetail document={selectedDocument} />}
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
                <DocumentScopeSelector
                  documents={documents}
                  mode={scopeMode}
                  selectedIds={selectedDocumentIds}
                  onModeChange={setScopeMode}
                  onToggleDocument={toggleScopeDocument}
                />
                <div className="mt-4 flex items-center justify-between gap-4 max-sm:flex-col max-sm:items-start">
                  <p className="text-sm text-[#4f5d50]">提交后仅返回带文件、页码和片段的资料依据。</p>
                  <button
                    disabled={questionSubmitDisabled}
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
                <article
                  key={match.id}
                  aria-current={sourceDetail?.id === match.id ? "true" : undefined}
                  className={`source-card ${sourceDetail?.id === match.id ? "ring-2 ring-[#7fa37e]" : ""}`}
                  data-testid="source-card"
                >
                  <div className="mb-3 flex min-w-0 items-start justify-between gap-3">
                    <button
                      type="button"
                      onClick={() => {
                        openSourceDetail(match).catch((err: Error) => setSourceDetailError(err.message));
                      }}
                      className="focus-ring min-w-0 rounded-md text-left"
                    >
                      <p className="break-all text-sm font-semibold text-[#203a2b]">
                        {match.rank}. {match.document_filename} 第 {match.page_no} 页
                      </p>
                      <p className="mt-1 text-xs text-[#5e6d5d]">
                        pgvector 相似度 {match.score.toFixed(4)} · {match.hit_reason}
                      </p>
                    </button>
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
              {(sourceDetail || sourceDetailError) && (
                <SourceReader
                  detail={sourceDetail}
                  error={sourceDetailError}
                  currentPage={currentSourcePage}
                  onPageChange={setCurrentSourcePage}
                />
              )}
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
      {documentToDelete && (
        <DocumentDeleteDialog
          document={documentToDelete}
          error={documentDialogError}
          busy={busy}
          onClose={closeDeleteDocumentDialog}
          onConfirm={deleteDocument}
        />
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

function DocumentDeleteDialog({
  document,
  error,
  busy,
  onClose,
  onConfirm
}: {
  document: DocumentRow;
  error: string;
  busy: boolean;
  onClose: () => void;
  onConfirm: () => void;
}) {
  return (
    <DialogFrame title="删除资料" onClose={onClose}>
      <div className="space-y-3 text-sm leading-6 text-[#3f5142]">
        <p className="font-semibold text-[#1f3428]">{document.filename}</p>
        <p>将删除该 PDF、页面文本、索引和相关来源结果。题目记录会保留。</p>
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
          删除资料
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

function DocumentScopeSelector({
  documents,
  mode,
  selectedIds,
  onModeChange,
  onToggleDocument
}: {
  documents: DocumentRow[];
  mode: "all" | "selected";
  selectedIds: number[];
  onModeChange: (mode: "all" | "selected") => void;
  onToggleDocument: (document: DocumentRow) => void;
}) {
  return (
    <section className="mt-4" data-testid="document-scope-selector">
      <div className="inline-grid rounded-md border border-[#c8d8c7] bg-[#f8fbf4] p-1 text-sm font-semibold text-[#315f43] sm:grid-cols-2">
        <button
          type="button"
          aria-pressed={mode === "all"}
          onClick={() => onModeChange("all")}
          className={`focus-ring rounded px-3 py-2 transition ${
            mode === "all" ? "bg-[#315f43] text-white shadow-sm" : "hover:bg-[#edf6e9]"
          }`}
        >
          全部可检索资料
        </button>
        <button
          type="button"
          aria-pressed={mode === "selected"}
          onClick={() => onModeChange("selected")}
          className={`focus-ring rounded px-3 py-2 transition ${
            mode === "selected" ? "bg-[#315f43] text-white shadow-sm" : "hover:bg-[#edf6e9]"
          }`}
        >
          指定资料
        </button>
      </div>

      {mode === "selected" && (
        <div className="mt-3 divide-y divide-[#dce4d7] border-y border-[#dce4d7]" data-testid="document-scope-list">
          {documents.length === 0 ? (
            <p className="py-4 text-sm text-[#516050]">项目内还没有资料。</p>
          ) : (
            documents.map((document) => {
              const disabledReason = documentScopeDisabledReason(document);
              const checked = selectedIds.includes(document.id);
              return (
                <label
                  key={document.id}
                  data-testid={`document-scope-option-${document.id}`}
                  className={`grid grid-cols-[auto_minmax(0,1fr)] gap-3 py-3 text-sm ${
                    disabledReason ? "cursor-not-allowed text-[#768074]" : "cursor-pointer text-[#26382d]"
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    disabled={Boolean(disabledReason)}
                    onChange={() => onToggleDocument(document)}
                    className="mt-1 h-4 w-4 accent-[#315f43]"
                  />
                  <span className="min-w-0">
                    <span className="block truncate font-semibold">{document.filename}</span>
                    <span className="mt-1 block text-xs text-[#516050]">
                      {document.text_quality_label} · {document.chunk_count} 个片段 · {document.searchable ? "可检索" : "不可检索"}
                      {disabledReason ? ` · ${disabledReason}` : ""}
                    </span>
                  </span>
                </label>
              );
            })
          )}
        </div>
      )}
    </section>
  );
}

function DocumentRowView({
  document,
  selected,
  onSelect,
  onDelete
}: {
  document: DocumentRow;
  selected: boolean;
  onSelect: (document: DocumentRow) => void;
  onDelete: (document: DocumentRow) => void;
}) {
  return (
    <div className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-start gap-3 py-4">
      <div className="mt-0.5 grid h-9 w-9 place-items-center rounded-md bg-[#e5efe0] text-[#315f43]">
        <FileText size={18} />
      </div>
      <button
        type="button"
        onClick={() => onSelect(document)}
        className={`focus-ring min-w-0 rounded-md px-2 py-1 text-left ${selected ? "bg-[#edf6e9] ring-1 ring-[#bfd3bf]" : "hover:bg-[#f8fbf4]"}`}
      >
        <p className="truncate text-sm font-semibold text-[#26382d]">{document.filename}</p>
        <p className="mt-1 text-xs text-[#516050]">
          {displayPages(document.page_count)} · {document.text_quality_label} · {document.chunk_count} 个片段 ·{" "}
          {document.searchable ? "可检索" : "不可检索"} · 最近处理 {formatDateTime(document.processed_at)}
          {document.failure_reason ? ` · ${document.failure_reason}` : ""}
        </p>
      </button>
      <div className="flex shrink-0 items-center gap-2">
        <Status value={document.status} />
        <button
          type="button"
          onClick={() => onDelete(document)}
          className="focus-ring inline-flex items-center gap-1 rounded-md border border-[#c98972] bg-[#fff8f4] px-2 py-1 text-xs font-semibold text-[#9d4d2f] hover:bg-[#fff1ec]"
        >
          <Trash2 size={14} />
          删除资料
        </button>
      </div>
    </div>
  );
}

function DocumentDetail({ document }: { document: DocumentRow }) {
  return (
    <section className="mt-5 border-t border-[#dce4d7] pt-5" data-testid="document-detail">
      <div className="mb-4 flex items-center gap-2 text-[#203a2b]">
        <FileText size={18} />
        <h4 className="text-base font-semibold">资料详情</h4>
      </div>
      <dl className="grid grid-cols-2 gap-x-5 gap-y-3 text-sm max-md:grid-cols-1">
        <DetailItem testId="filename" label="文件名" value={document.filename} />
        <DetailItem testId="content-type" label="内容类型" value={document.content_type} />
        <DetailItem testId="page-count" label="页数" value={displayNumber(document.page_count)} />
        <DetailItem testId="extractable-page-count" label="可提取文字页数" value={displayNumber(document.extractable_page_count)} />
        <DetailItem testId="text-quality" label="文字层质量" value={document.text_quality_label} />
        <DetailItem testId="chunk-count" label="chunk 数" value={displayNumber(document.chunk_count)} />
        <DetailItem testId="searchable" label="可检索状态" value={document.searchable ? "可检索" : "不可检索"} />
        <DetailItem testId="status" label="处理状态" value={statusLabel(document.status)} />
        <DetailItem testId="processing-stage" label="处理阶段" value={processingStageLabel(document.processing_stage)} />
        <DetailItem testId="failed-stage" label="失败阶段" value={document.failed_stage ? processingStageLabel(document.failed_stage) : "无"} />
        <DetailItem testId="failure-code" label="失败码" value={document.failure_code ?? "无"} />
        <DetailItem testId="failure-reason" label="失败原因" value={document.failure_reason ?? "无"} />
        <DetailItem testId="created-at" label="创建时间" value={formatDateTime(document.created_at)} />
        <DetailItem testId="processed-at" label="最近处理时间" value={formatDateTime(document.processed_at)} />
      </dl>
    </section>
  );
}

function SourceReader({
  detail,
  error,
  currentPage,
  onPageChange
}: {
  detail: SourceDetail | null;
  error: string;
  currentPage: number | null;
  onPageChange: (page: number) => void;
}) {
  if (error) {
    const missingFile = error === "资料文件不存在";
    return (
      <section className="rounded-md border border-[#c98972] bg-[#fff8f4] p-4" data-testid="source-reader-error">
        <div className="mb-2 flex items-center gap-2 font-semibold text-[#9d4d2f]">
          <AlertTriangle size={17} />
          {missingFile ? "资料文件不存在" : "来源已失效"}
        </div>
        <p className="text-sm leading-6 text-[#6e4a3b]">{missingFile ? "无法打开原 PDF 文件。" : "该来源已被删除或重新处理。"}</p>
      </section>
    );
  }
  if (!detail || currentPage === null) return null;

  const pdfUrl = `${apiUrl}${detail.pdf_url.replace(/#page=\d+$/, `#page=${currentPage}`)}`;
  const atHitPage = currentPage === detail.page_no;

  return (
    <section className="rounded-md border border-[#c8d8c7] bg-[#fbfcf8]" data-testid="source-reader">
      <div className="border-b border-[#dce4d7] px-4 py-3">
        <div className="mb-3 flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-[#203a2b]" data-testid="source-reader-filename">
              {detail.filename}
            </p>
            <p className="mt-1 text-xs text-[#5e6d5d]" data-testid="source-reader-meta">
              第 {currentPage} / {detail.page_count} 页 · 排序 {detail.rank} · {detail.confidence_label}
            </p>
          </div>
          {atHitPage && (
            <span className="shrink-0 rounded-full border border-[#b9d0b9] bg-[#edf6e9] px-2 py-1 text-xs font-semibold text-[#315f43]">
              命中页
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            aria-label="上一页"
            disabled={currentPage <= 1}
            onClick={() => onPageChange(currentPage - 1)}
            className="focus-ring grid h-8 w-8 place-items-center rounded-md border border-[#c6d6c5] bg-[#f8fbf4] text-[#315f43] disabled:opacity-45"
          >
            <ChevronLeft size={16} />
          </button>
          <button
            type="button"
            aria-label="下一页"
            disabled={currentPage >= detail.page_count}
            onClick={() => onPageChange(currentPage + 1)}
            className="focus-ring grid h-8 w-8 place-items-center rounded-md border border-[#c6d6c5] bg-[#f8fbf4] text-[#315f43] disabled:opacity-45"
          >
            <ChevronRight size={16} />
          </button>
          <button
            type="button"
            disabled={atHitPage}
            onClick={() => onPageChange(detail.page_no)}
            className="focus-ring rounded-md border border-[#c6d6c5] bg-[#f8fbf4] px-3 py-2 text-xs font-semibold text-[#315f43] disabled:opacity-45"
          >
            回到命中页
          </button>
          <a
            href={pdfUrl}
            target="_blank"
            className="focus-ring ml-auto inline-flex items-center gap-1 rounded-md border border-[#b8cdb8] bg-[#edf6e9] px-2 py-2 text-xs font-semibold text-[#315f43] hover:bg-[#dfeedd]"
          >
            <ArrowUpRight size={14} />
            PDF
          </a>
        </div>
      </div>
      <div className="h-[360px] border-b border-[#dce4d7] bg-[#eef2e9]">
        <iframe title="PDF 阅读" src={pdfUrl} className="h-full w-full" data-testid="source-reader-pdf" />
      </div>
      <div className="space-y-3 px-4 py-4 text-sm leading-6 text-[#435244]">
        <p className="text-xs font-semibold text-[#637061]">命中原因</p>
        <p data-testid="source-reader-hit-reason">{detail.hit_reason}</p>
        <p className="text-xs font-semibold text-[#637061]">命中段落</p>
        <p className="break-words font-semibold text-[#203a2b]" data-testid="source-reader-source-text">
          {detail.source_text}
        </p>
        <p className="text-xs font-semibold text-[#637061]">上下文</p>
        <p className="break-words" data-testid="source-reader-context">
          {detail.context_before}
          <mark className="bg-[#fff0b8] px-1 text-[#203a2b]">{detail.source_text}</mark>
          {detail.context_after}
        </p>
        <p className="text-xs text-[#5e6d5d]" data-testid="source-reader-score">
          pgvector 相似度 {detail.score.toFixed(4)} · chunk {detail.chunk_id}
        </p>
      </div>
    </section>
  );
}

function DetailItem({ testId, label, value }: { testId: string; label: string; value: string }) {
  return (
    <div className="min-w-0" data-testid={`document-detail-${testId}`}>
      <dt className="text-xs font-semibold text-[#637061]">{label}</dt>
      <dd className="mt-1 break-words text-[#25382d]">{value}</dd>
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

function processingStageLabel(value: string) {
  const labels: Record<string, string> = {
    uploaded: "已上传",
    extracting_text: "提取文本",
    chunking: "切分片段",
    embedding: "生成向量",
    indexing: "写入索引",
    completed: "完成",
    failed: "失败"
  };
  return labels[value] ?? value;
}

function displayNumber(value: number | null) {
  return value === null ? "无" : String(value);
}

function displayPages(value: number | null) {
  return value === null ? "等待页数" : `${value} 页`;
}

function documentScopeDisabledReason(document: DocumentRow) {
  if (document.status !== "completed") return "资料尚未完成处理";
  if (document.text_quality === "unsearchable") return "资料不可检索";
  if (document.chunk_count === 0) return "暂无可检索片段";
  return null;
}

function formatDateTime(value: string | null) {
  if (!value) return "无";
  const date = new Date(value);
  const pad = (part: number) => String(part).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(
    date.getSeconds()
  )}`;
}

function hasSource(match: Match) {
  return Boolean(match.document_filename && match.page_no && match.source_text.trim() && match.pdf_url);
}
