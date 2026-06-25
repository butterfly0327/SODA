export type ResourceKind = 'dataset' | 'api';

export interface ResourceReviewSummary {
  id: number;
  authorId?: string;
  author: string;
  rating: number;
  content: string;
  createdAt: string | null;
}

export interface BaseResultCard {
  id?: number;
  type: ResourceKind;
  name: string;
  score?: number;
  isBookmarked?: boolean;
  bookmarkId?: number | null;
  rawRecommendationScore?: number;
  rank?: number;
  updatedAt?: string;
  reasons?: string[];
  isFree?: boolean;
  reviews?: ResourceReviewSummary[];
}

export interface DatasetCard extends BaseResultCard {
  type: 'dataset';
  source?: string;
  subtitle?: string;
  descriptionShort?: string;
  descriptionLong?: string;
  domains?: string[];
  tasks?: string[];
  modalities?: string[];
  tags?: string[];
  languages?: string[];
  licenseName?: string;
  licenseUrl?: string;
  commercialUseAllowed?: boolean | null;
  taskMatch?: number;
  projectType?: string;
  classCount?: number;
  rowCount?: number | null;
  sampleCount?: string;
  dataSize?: string;
  license?: string;
  missingRate?: number;
  reliability?: 'High' | 'Medium' | 'Low' | string;
  lastUpdate?: string;
  datasetSizeBytes?: number | null;
  metrics?: unknown;
  schemaJson?: unknown;
  canonicalUrl?: string;
  landingUrl?: string;
}

export interface APICard extends BaseResultCard {
  type: 'api';
  description?: string;
  provider?: string;
  baseUrl?: string;
  docsUrl?: string;
  category?: string;
  tags?: string[];
  rateLimit?: number | null;
  responseTime?: string;
  responseFormat?: string;
  auth?: string;
  freeQuota?: string;
  pricingNote?: string;
  commercialUse?: boolean | null;
  requiresApproval?: boolean | null;
  availability?: string;
  responseSchema?: unknown;
  pricingNote?: string;
}

export type ResultCard = DatasetCard | APICard;

export interface SearchResultData {
  projectType?: string;
  totalCandidates: number;
  recommendations: number;
  analysis: string;
  results: ResultCard[];
  searchQuery?: string;
}
