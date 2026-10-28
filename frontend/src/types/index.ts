export type BankId = 'NEXUS' | 'APEX' | 'CREST' | 'VANGUARD';

export type AccountRiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface Bank {
  id: string;
  name: string;
  code: string;
  account_count?: number;
  transaction_count?: number;
}

export interface Account {
  id: string;
  bank_id: string;
  account_number: string;
  holder_name: string;
  account_type: string;
  status: string;
  risk_score: number;
  risk_level: AccountRiskLevel;
  tags?: string[];
  created_at: string;
}

export interface Transaction {
  id: string;
  bank_id: string;
  raw_reference: string;
  originator_account_id: string;
  beneficiary_account_id: string;
  originator_account_number?: string;
  beneficiary_account_number?: string;
  originator_bank?: string;
  beneficiary_bank?: string;
  amount: number;
  currency: string;
  timestamp: string;
  channel: string;
  transaction_type: string;
  status: string;
  risk_score: number;
  tags?: string[];
  normalisation_status: string;
  cbdc_token_id?: string;
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  bank_id: string;
  bank_name?: string;
  risk_score: number;
  risk_level: AccountRiskLevel;
  is_source?: boolean;
  is_sink?: boolean;
  is_mule?: boolean;
  fan_in?: number;
  fan_out?: number;
  in_degree?: number;
  out_degree?: number;
  total_inflow?: number;
  total_outflow?: number;
  tags?: string[];
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  amount: number;
  currency: string;
  timestamp: string;
  transaction_id: string;
  risk_score: number;
  cbdc_token_id?: string;
}

export interface NetworkGraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  summary?: {
    total_nodes: number;
    total_edges: number;
    total_volume: number;
    mule_count: number;
    cycles_detected: number;
  };
}

export interface ProvenanceRecord {
  id: string;
  transaction_id: string;
  parent_id?: string | null;
  mode: 'CONVENTIONAL' | 'CBDC';
  source_account: string;
  sink_account: string;
  amount: number;
  retained_amount?: number;
  hops: number;
  token_id?: string;
  parent_token_id?: string;
  conservation_valid?: boolean;
  lineage_path?: string[];
  created_at: string;
}

export interface RiskAlert {
  id: string;
  investigation_id?: string;
  account_id: string;
  transaction_id?: string;
  title: string;
  description: string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  status: 'NEW' | 'UNDER_REVIEW' | 'CONFIRMED_FRAUD' | 'FALSE_POSITIVE' | 'CLOSED';
  score: number;
  rule_code: string;
  metrics?: Record<string, any>;
  created_at: string;
  updated_at?: string;
}

export interface Investigation {
  id: string;
  case_number: string;
  title: string;
  description?: string;
  status: 'OPEN' | 'IN_PROGRESS' | 'COMPLETED' | 'ARCHIVED';
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  scenario_type?: string;
  nodes_count?: number;
  transactions_count?: number;
  total_flagged_amount?: number;
  created_at: string;
  updated_at?: string;
}

export interface ScenarioRunResult {
  scenario_id: string;
  scenario_name: string;
  accounts_generated: number;
  transactions_generated: number;
  ground_truth_mules: string[];
  detected_mules: string[];
  precision: number;
  recall: number;
  f1_score: number;
  investigation_id: string;
  total_volume: number;
}

export interface DashboardSummary {
  total_transactions: number;
  total_volume: number;
  total_flagged_volume: number;
  active_investigations: number;
  high_risk_alerts: number;
  mules_identified: number;
  banks_connected: number;
  provenance_records_count: number;
}
