import {
  FileText,
  Layers,
  MessageSquareText,
  Quote,
  Search,
  ShieldCheck,
  Sparkles,
  UploadCloud,
  Zap,
  type LucideIcon,
} from "lucide-react";

export interface NavLink {
  href: string;
  label: string;
}

export interface MarketingFeature {
  icon: LucideIcon;
  title: string;
  description: string;
}

export interface MarketingStat {
  value: string;
  label: string;
}

export interface MarketingFaq {
  question: string;
  answer: string;
}

export interface DemoCitation {
  document: string;
  page: number;
}

export interface DemoQuery {
  question: string;
  answer: string;
  citations: readonly DemoCitation[];
}

export interface WorkflowDetail {
  icon: LucideIcon;
  label: string;
  meta: string;
}

export interface WorkflowStep {
  icon: LucideIcon;
  title: string;
  description: string;
  details: readonly WorkflowDetail[];
}

export const NAV_LINKS: readonly NavLink[] = [
  { href: "#features", label: "Features" },
  { href: "#how-it-works", label: "How it works" },
  { href: "#faq", label: "FAQ" },
];

export const MARKETING_FEATURES: readonly MarketingFeature[] = [
  {
    icon: Search,
    title: "Semantic search",
    description:
      "Find the most relevant passages by meaning, not just matching keywords.",
  },
  {
    icon: MessageSquareText,
    title: "Grounded answers",
    description:
      "Every response is generated from your documents, with guardrails against guesswork.",
  },
  {
    icon: Quote,
    title: "Page-level citations",
    description:
      "Trace answers back to the exact document and page without hunting for the source.",
  },
  {
    icon: Zap,
    title: "Streaming responses",
    description:
      "Answers arrive token by token, so you start reading before generation finishes.",
  },
  {
    icon: Layers,
    title: "Scoped to a document",
    description:
      "Ask across your whole library or narrow the conversation to a single file.",
  },
  {
    icon: ShieldCheck,
    title: "Private workspace",
    description:
      "Your uploads are isolated to your account and never mixed with anyone else's.",
  },
];

export const MARKETING_STATS: readonly MarketingStat[] = [
  { value: "Top-5", label: "chunks retrieved per question" },
  { value: "< 2s", label: "to first streamed token" },
  { value: "100%", label: "answers with citations" },
];

export const MARKETING_FAQS: readonly MarketingFaq[] = [
  {
    question: "What kind of documents can I upload?",
    answer:
      "PDFs today — handbooks, contracts, research papers, policies. Text is extracted page by page so citations stay accurate.",
  },
  {
    question: "How do I know the answer is real?",
    answer:
      "Every answer is generated only from retrieved passages, and each response links back to the document and page it came from so you can verify it yourself.",
  },
  {
    question: "Can other people see my documents?",
    answer:
      "No. Documents are scoped to your account, and every query is filtered to your own library before retrieval runs.",
  },
];

export const DEMO_DOCUMENTS: readonly string[] = [
  "Product handbook.pdf",
  "Security policy.pdf",
  "Billing terms.pdf",
];

export const DEMO_QUERIES: readonly DemoQuery[] = [
  {
    question: "What is the refund policy for annual plans?",
    answer:
      "Annual plans are refundable within 30 days of purchase, as long as usage stays below the fair-use threshold. Refunds are issued to the original payment method [Source 1].",
    citations: [
      { document: "Product handbook.pdf", page: 12 },
      { document: "Billing terms.pdf", page: 4 },
    ],
  },
  {
    question: "How long is customer data retained?",
    answer:
      "Customer data is retained for 90 days after account closure, then permanently deleted from primary storage and backups [Source 1].",
    citations: [{ document: "Security policy.pdf", page: 7 }],
  },
  {
    question: "Who approves vendor security reviews?",
    answer:
      "The security lead approves vendor reviews, and any vendor handling personal data also requires sign-off from the data protection officer [Source 1].",
    citations: [
      { document: "Security policy.pdf", page: 15 },
      { document: "Vendor checklist.pdf", page: 2 },
    ],
  },
];

export const WORKFLOW_STEPS: readonly WorkflowStep[] = [
  {
    icon: UploadCloud,
    title: "Upload a PDF",
    description:
      "Drop in the handbook, contract, or policy you need answers from. Parsing starts immediately.",
    details: [
      { icon: FileText, label: "Product handbook.pdf", meta: "2.4 MB · 48 pages" },
      { icon: Search, label: "Extracting text", meta: "page by page" },
    ],
  },
  {
    icon: Sparkles,
    title: "We make it searchable",
    description:
      "Content is chunked with overlap, embedded, and stored in pgvector for meaning-based retrieval.",
    details: [
      { icon: Layers, label: "184 chunks created", meta: "1,000 chars · 150 overlap" },
      { icon: Sparkles, label: "Embeddings stored", meta: "pgvector index" },
    ],
  },
  {
    icon: MessageSquareText,
    title: "Ask naturally",
    description:
      "Your question retrieves the top matching passages, and the answer streams back with citations.",
    details: [
      { icon: Search, label: "Top-5 chunks retrieved", meta: "cosine similarity" },
      { icon: Quote, label: "Answer streaming", meta: "grounded + cited" },
    ],
  },
];

/** Animation tuning for the marketing hero demo and workflow carousel. */
export const DEMO_TYPING_INTERVAL_MS = 16;
export const DEMO_RETRIEVAL_DELAY_MS = 620;
export const WORKFLOW_AUTO_ADVANCE_MS = 5000;
