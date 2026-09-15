// Shared domain types — the single source of truth for API shapes on the frontend.
// Kills scattered `any` and gives the compiler real leverage over UI code.

export type ProjectState =
  | 'IDEA' | 'PROPOSED' | 'TEAM_FORMING' | 'PLANNING'
  | 'DEVELOPMENT' | 'TESTING' | 'DEMO' | 'COMPLETED' | 'SHOWCASE'

export interface ProjectCard {
  id: number
  slug: string
  title: string
  problem: string
  state: ProjectState
  required_skills: string[]
  tech: string[]
  team_size: number
  member_count: number
  showcase: boolean
  owner_id: number
  mentor_id: number | null
  repo_url: string
  demo_url: string
  is_member: boolean
}

export interface GitHubCommit {
  sha: string
  message: string
  author: string
  date: string
  url: string
}

export interface GitHubStats {
  linked: boolean
  reason?: string
  repo?: string
  url?: string
  stars?: number
  forks?: number
  open_issues?: number
  language?: string | null
  description?: string | null
  pushed_at?: string
  commits?: GitHubCommit[]
  error?: string
  detail?: string
}

export interface Reward {
  id: number
  name: string
  description: string
  cost: number
  kind: 'physical' | 'perk' | 'digital'
  icon: string
  stock: number
  active: boolean
  sold_out: boolean
  affordable?: boolean
}

export interface Wallet {
  balance: number
  lifetime: number
}

export interface AutoIssue { level: 'error' | 'warn' | 'info'; msg: string }
export interface AutoReport {
  score: number
  issues: AutoIssue[]
  metrics: { lines: number; code_lines?: number; longest_line?: number }
}
export interface PeerReviewOut {
  reviewer: string
  correctness: number
  readability: number
  efficiency: number
  comment: string
  created_at: string
}
export interface CodeSubmission {
  id: number
  title: string
  language: string
  description: string
  author: { id: number; name: string; avatar_seed: string } | null
  auto_score: number
  auto_report: AutoReport
  status: 'open' | 'graded'
  review_goal: number
  review_count: number
  final_score: number
  created_at: string
  code?: string
  reviews?: PeerReviewOut[]
  is_author?: boolean
  has_reviewed?: boolean
  can_review?: boolean
}
export interface ActivityItem {
  id: number
  kind: string
  icon: string
  actor: string
  text: string
  link: string
  points: number
  created_at: string
}
