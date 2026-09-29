import type {
  Athlete,
  AthleteCreate,
  AthleteUpdate,
  BenchmarkSource,
  PerformanceEvent,
  PerformanceEventCreate,
  PerformanceEventUpdate,
  Benchmarks,
  ZScoreResult,
  ReferenceGroup,
  UploadResult,
  TrainingSession,
  TrainingSessionCreate,
  TrainingSessionUpdate,
  BatchSessionAssign,
  BatchSessionResponse,
  TrainingLoadAnalysis,
  ExercisePrescription,
  ExercisePrescriptionCreate,
  ExercisePrescriptionUpdate,
  WellnessEntry,
  WellnessEntryCreate,
  WellnessEntryUpdate,
  ExerciseLibraryItem,
  ExerciseLibraryCreate,
  ExerciseLibraryUpdate,
  SessionTemplate,
  SessionTemplateCreate,
  SessionTemplateUpdate,
  AirBikeTest,
  AirBikeTestListItem,
  AirBikeTestCreate,
  AirBikeTestUpdate,
  MovementAssessment,
  MovementAssessmentListItem,
  MovementAssessmentCreate,
  MovementAssessmentUpdate,
  AssessmentPhoto,
  InvitationResponse,
  InvitationValidateResponse,
  TestReport,
  TestReportListItem,
  TestReportCreate,
  TestReportUpdate,
  ProgramPackage,
  ProgramPackageDetail,
  ProgramPackageCreate,
  ProgramPackageUpdate,
  ProgramTemplate,
  ProgramTemplateCreate,
  ProgramTemplateUpdate,
  InstalledProgramTemplate,
  AirBikeRecording,
  AirBikeRecordingCreate,
  AirBikeRecordingListItem,
  TrainingBlock,
  TrainingBlockDetail,
  TrainingBlockCreate,
  TrainingBlockUpdate,
  BlockSession,
  BlockSessionCreate,
  BlockSessionUpdate,
  BlockApplyRequest,
  BlockApplyResponse,
  BlockPreviewResponse,
  AthleteMax,
  AthleteMaxUpsert,
  ProgrammeForm,
  ProgrammeFormData,
  CombineAttempt,
  CombineAttemptSubmit,
  CombineEvent,
  CombineEventCreate,
  CombineEventListItem,
  CombineEventUpdate,
  CombineFilterQuery,
  CombineLeaderboard,
  CombineMeasures,
  CombineParticipant,
  CombineRosterResult,
  CombineRosterRow,
  CombineShareToken,
  CombineStation,
  CombineStationRoster,
} from './types';

const API_BASE = '/api/v1';

// Auth error event system for 401 interceptor
type AuthErrorListener = () => void;
const authErrorListeners: Set<AuthErrorListener> = new Set();

export function onAuthError(listener: AuthErrorListener): () => void {
  authErrorListeners.add(listener);
  return () => { authErrorListeners.delete(listener); };
}

function notifyAuthError() {
  authErrorListeners.forEach((listener) => listener());
}

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

/** What a station operator is told when a save never came back. */
const TIMEOUT_MESSAGE = 'Timed out — check the connection and tap SAVE again';

interface ValidationErrorItem {
  loc?: (string | number)[];
  msg?: string;
}

/**
 * FastAPI returns a 422 `detail` as an array of validation objects, which reaches
 * a station iPad as "[object Object]" — telling the operator nothing about which
 * field was rejected. Name the field, and drop pydantic's "Value error," prefix.
 */
function formatDetail(detail: unknown, fallback: string): string {
  if (typeof detail === 'string') return detail || fallback;
  if (Array.isArray(detail)) {
    const lines = (detail as ValidationErrorItem[])
      .map((item) => {
        const msg = (item?.msg ?? '').replace(/^Value error,\s*/, '');
        // The last named segment of `loc` is the field; 'body' and friends are noise.
        const field = [...(item?.loc ?? [])]
          .reverse()
          .find((part) => typeof part === 'string' && !['body', 'query', 'path'].includes(part));
        if (!msg) return typeof field === 'string' ? field : '';
        return field ? `${field}: ${msg}` : msg;
      })
      .filter(Boolean);
    if (lines.length) return lines.join('; ');
  }
  return fallback;
}

export async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit,
  opts?: { timeoutMs?: number }
): Promise<T> {
  // Opt-in, never a global default: CSV upload and block apply legitimately run
  // long. Station calls pass one so a lost response cannot leave SAVE spinning.
  const controller = opts?.timeoutMs ? new AbortController() : null;
  let timedOut = false;
  const timer = controller
    ? setTimeout(() => {
        timedOut = true;
        controller.abort();
      }, opts?.timeoutMs)
    : null;

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${endpoint}`, {
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
      ...(controller ? { signal: controller.signal } : {}),
    });
  } catch (err) {
    if (timedOut) throw new ApiError(408, TIMEOUT_MESSAGE);
    throw err;
  } finally {
    if (timer) clearTimeout(timer);
  }

  if (!response.ok) {
    // Global 401 interceptor: expired session -> redirect to login
    if (response.status === 401 && !endpoint.startsWith('/auth/')) {
      notifyAuthError();
    }
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new ApiError(response.status, formatDetail(error?.detail, 'Request failed'));
  }

  // 204 No Content — no body to parse (DELETE endpoints)
  if (response.status === 204) return undefined as unknown as T;

  return response.json();
}

// Auth API
export interface AuthResponse {
  user_id: string;
  email: string;
}

export const authApi = {
  login: (email: string, password: string) =>
    fetchApi<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  signup: (email: string, password: string) =>
    fetchApi<AuthResponse>('/auth/signup', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  logout: () =>
    fetchApi<void>('/auth/logout', { method: 'POST' }),

  me: () =>
    fetchApi<{ user_id: string; role: string; email?: string; athlete_id?: string }>('/auth/me'),

  forgotPassword: (email: string) =>
    fetchApi<{ message: string }>('/auth/forgot-password', {
      method: 'POST',
      body: JSON.stringify({ email }),
    }),

  resetPassword: (newPassword: string, accessToken?: string | null, code?: string | null) =>
    fetchApi<{ message: string }>('/auth/reset-password', {
      method: 'POST',
      body: JSON.stringify({
        new_password: newPassword,
        ...(accessToken ? { access_token: accessToken } : {}),
        ...(code ? { code } : {}),
      }),
    }),

  changePassword: (currentPassword: string, newPassword: string) =>
    fetchApi<{ message: string }>('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    }),

  changeEmail: (currentPassword: string, newEmail: string) =>
    fetchApi<{ message: string }>('/auth/change-email', {
      method: 'POST',
      body: JSON.stringify({ current_password: currentPassword, new_email: newEmail }),
    }),
};

// Athletes API
export const athletesApi = {
  list: () => fetchApi<Athlete[]>('/athletes/?limit=200'),

  get: (id: string) => fetchApi<Athlete>(`/athletes/${id}`),

  create: (data: AthleteCreate) =>
    fetchApi<Athlete>('/athletes/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (id: string, data: AthleteUpdate) =>
    fetchApi<Athlete>(`/athletes/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    fetchApi<void>(`/athletes/${id}`, { method: 'DELETE' }),

  deleteAll: (currentPassword: string) =>
    fetchApi<{ deleted_athletes: number; deleted_events: number }>('/athletes/', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ current_password: currentPassword }),
    }),

  merge: (keepId: string, mergeId: string) =>
    fetchApi<{ kept_athlete_id: string; merged_events: number; deleted_athlete_id: string }>(
      '/athletes/merge',
      { method: 'POST', body: JSON.stringify({ keep_id: keepId, merge_id: mergeId }) }
    ),
};

// Events API
export const eventsApi = {
  listForAthlete: (
    athleteId: string,
    options?: { startDate?: string; endDate?: string }
  ) => {
    const params = new URLSearchParams();
    if (options?.startDate) params.set('start_date', options.startDate);
    if (options?.endDate) params.set('end_date', options.endDate);
    const query = params.toString();
    return fetchApi<PerformanceEvent[]>(
      `/events/athlete/${athleteId}${query ? `?${query}` : ''}`
    );
  },

  get: (id: string) => fetchApi<PerformanceEvent>(`/events/${id}`),

  create: (data: PerformanceEventCreate) =>
    fetchApi<PerformanceEvent>('/events/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (id: string, data: PerformanceEventUpdate) =>
    fetchApi<PerformanceEvent>(`/events/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    fetchApi<void>(`/events/${id}`, { method: 'DELETE' }),
};

// Analysis API
export const analysisApi = {
  getBenchmarks: (params: {
    metric: string;
    referenceGroup: ReferenceGroup;
    gender?: 'male' | 'female';
    massBand?: string;
    benchmarkSource?: BenchmarkSource;
    startDate?: string;
    endDate?: string;
  }) => {
    const searchParams = new URLSearchParams({
      metric: params.metric,
      reference_group: params.referenceGroup,
    });
    if (params.gender) searchParams.set('gender', params.gender);
    if (params.massBand) searchParams.set('mass_band', params.massBand);
    if (params.benchmarkSource) searchParams.set('benchmark_source', params.benchmarkSource);
    if (params.startDate) searchParams.set('start_date', params.startDate);
    if (params.endDate) searchParams.set('end_date', params.endDate);

    return fetchApi<Benchmarks>(`/analysis/benchmarks?${searchParams}`);
  },

  getZScore: (
    athleteId: string,
    params: {
      metric: string;
      referenceGroup: ReferenceGroup;
      eventId?: string;
      benchmarkSource?: BenchmarkSource;
      startDate?: string;
      endDate?: string;
    }
  ) => {
    const searchParams = new URLSearchParams({
      metric: params.metric,
      reference_group: params.referenceGroup,
    });
    if (params.eventId) searchParams.set('event_id', params.eventId);
    if (params.benchmarkSource) searchParams.set('benchmark_source', params.benchmarkSource);
    if (params.startDate) searchParams.set('start_date', params.startDate);
    if (params.endDate) searchParams.set('end_date', params.endDate);

    return fetchApi<ZScoreResult>(
      `/analysis/athlete/${athleteId}/zscore?${searchParams}`
    );
  },

  getZScoresBulk: (
    athleteId: string,
    params: {
      metric: string;
      referenceGroup: ReferenceGroup;
      benchmarkSource?: BenchmarkSource;
      startDate?: string;
      endDate?: string;
    }
  ) => {
    const searchParams = new URLSearchParams({
      metric: params.metric,
      reference_group: params.referenceGroup,
    });
    if (params.benchmarkSource) searchParams.set('benchmark_source', params.benchmarkSource);
    if (params.startDate) searchParams.set('start_date', params.startDate);
    if (params.endDate) searchParams.set('end_date', params.endDate);

    return fetchApi<Record<string, ZScoreResult>>(
      `/analysis/athlete/${athleteId}/zscores?${searchParams}`
    );
  },

  getAvailableMetrics: (athleteId: string, options?: { startDate?: string; endDate?: string }) => {
    const params = new URLSearchParams();
    if (options?.startDate) params.set('start_date', options.startDate);
    if (options?.endDate) params.set('end_date', options.endDate);
    const query = params.toString();
    return fetchApi<string[]>(
      `/analysis/athlete/${athleteId}/metrics${query ? `?${query}` : ''}`
    );
  },
};

// Upload API
export const uploadApi = {
  uploadCsv: async (file: File, athleteId?: string): Promise<UploadResult> => {
    const formData = new FormData();
    formData.append('file', file);

    const url = athleteId
      ? `${API_BASE}/uploads/csv?athlete_id=${athleteId}`
      : `${API_BASE}/uploads/csv`;

    const response = await fetch(url, {
      method: 'POST',
      credentials: 'include',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
      throw new ApiError(response.status, formatDetail(error?.detail, 'Upload failed'));
    }

    return response.json();
  },

  previewCsv: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE}/uploads/csv/preview`, {
      method: 'POST',
      credentials: 'include',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Preview failed' }));
      throw new ApiError(response.status, formatDetail(error?.detail, 'Preview failed'));
    }

    return response.json();
  },
};

// Training API
export const trainingApi = {
  listSessions: (
    athleteId: string,
    options?: { startDate?: string; endDate?: string }
  ) => {
    const params = new URLSearchParams();
    if (options?.startDate) params.set('start_date', options.startDate);
    if (options?.endDate) params.set('end_date', options.endDate);
    const query = params.toString();
    return fetchApi<TrainingSession[]>(
      `/training/sessions/athlete/${athleteId}${query ? `?${query}` : ''}`
    );
  },

  getSession: (id: string) =>
    fetchApi<TrainingSession>(`/training/sessions/${id}`),

  createSession: (data: TrainingSessionCreate) =>
    fetchApi<TrainingSession>('/training/sessions/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateSession: (id: string, data: TrainingSessionUpdate) =>
    fetchApi<TrainingSession>(`/training/sessions/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  deleteSession: (id: string) =>
    fetchApi<void>(`/training/sessions/${id}`, { method: 'DELETE' }),

  getLoadAnalysis: (athleteId: string, days: number = 28) =>
    fetchApi<TrainingLoadAnalysis>(`/training/analysis/load/${athleteId}?days=${days}`),

  batchAssign: (data: BatchSessionAssign) =>
    fetchApi<BatchSessionResponse>('/training/sessions/batch', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
};

// Training Types API
export interface TrainingTypeItem {
  type_name: string;
  is_system: boolean;
  id?: string;
}

export const trainingTypesApi = {
  list: () => fetchApi<TrainingTypeItem[]>('/training/types/'),

  create: (typeName: string) =>
    fetchApi<TrainingTypeItem>('/training/types/', {
      method: 'POST',
      body: JSON.stringify({ type_name: typeName }),
    }),

  delete: (id: string) =>
    fetchApi<void>(`/training/types/${id}`, { method: 'DELETE' }),
};

// Exercises API
export const exercisesApi = {
  list: (sessionId: string) =>
    fetchApi<ExercisePrescription[]>(`/training/sessions/${sessionId}/exercises/`),

  create: (sessionId: string, data: ExercisePrescriptionCreate) =>
    fetchApi<ExercisePrescription>(`/training/sessions/${sessionId}/exercises/`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (sessionId: string, exerciseId: string, data: ExercisePrescriptionUpdate) =>
    fetchApi<ExercisePrescription>(`/training/sessions/${sessionId}/exercises/${exerciseId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  delete: (sessionId: string, exerciseId: string) =>
    fetchApi<void>(`/training/sessions/${sessionId}/exercises/${exerciseId}`, {
      method: 'DELETE',
    }),
};

// Wellness API
export const wellnessApi = {
  listEntries: (
    athleteId: string,
    options?: { startDate?: string; endDate?: string }
  ) => {
    const params = new URLSearchParams();
    if (options?.startDate) params.set('start_date', options.startDate);
    if (options?.endDate) params.set('end_date', options.endDate);
    const query = params.toString();
    return fetchApi<WellnessEntry[]>(
      `/wellness/athlete/${athleteId}${query ? `?${query}` : ''}`
    );
  },

  getEntry: (id: string) =>
    fetchApi<WellnessEntry>(`/wellness/${id}`),

  createEntry: (data: WellnessEntryCreate) =>
    fetchApi<WellnessEntry>('/wellness/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateEntry: (id: string, data: WellnessEntryUpdate) =>
    fetchApi<WellnessEntry>(`/wellness/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  deleteEntry: (id: string) =>
    fetchApi<void>(`/wellness/${id}`, { method: 'DELETE' }),
};

// Exercise Library API
export const exerciseLibraryApi = {
  list: (options?: { search?: string; category?: string }) => {
    const params = new URLSearchParams();
    if (options?.search) params.set('search', options.search);
    if (options?.category) params.set('category', options.category);
    const query = params.toString();
    return fetchApi<ExerciseLibraryItem[]>(
      `/exercise-library/${query ? `?${query}` : ''}`
    );
  },

  create: (data: ExerciseLibraryCreate) =>
    fetchApi<ExerciseLibraryItem>('/exercise-library/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (id: string, data: ExerciseLibraryUpdate) =>
    fetchApi<ExerciseLibraryItem>(`/exercise-library/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    fetchApi<void>(`/exercise-library/${id}`, { method: 'DELETE' }),
};

// Session Templates API
export interface TargetPreviewExercise {
  exercise_name: string;
  intensity_type: string | null;
  intensity_min: number | null;
  intensity_max: number | null;
  source: string;
}

export interface TargetPreviewResponse {
  template_id: string;
  athlete_id: string;
  tier: string | null;
  exercises: TargetPreviewExercise[];
}

export const sessionTemplatesApi = {
  list: () => fetchApi<SessionTemplate[]>('/session-templates/'),

  listGoldStandard: () =>
    fetchApi<SessionTemplate[]>('/session-templates/?category=conditioning'),

  get: (id: string) => fetchApi<SessionTemplate>(`/session-templates/${id}`),

  previewTargets: (templateId: string, athleteId: string) =>
    fetchApi<TargetPreviewResponse>(
      `/session-templates/${templateId}/preview-targets?athlete_id=${athleteId}`
    ),

  create: (data: SessionTemplateCreate) =>
    fetchApi<SessionTemplate>('/session-templates/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (id: string, data: SessionTemplateUpdate) =>
    fetchApi<SessionTemplate>(`/session-templates/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    fetchApi<void>(`/session-templates/${id}`, { method: 'DELETE' }),

  apply: (templateId: string, sessionId: string) =>
    fetchApi<ExercisePrescription[]>(
      `/session-templates/${templateId}/apply?session_id=${sessionId}`,
      { method: 'POST' }
    ),
};

// Air Bike Tests API
export const airBikeApi = {
  listTests: (athleteId: string) =>
    fetchApi<AirBikeTestListItem[]>(`/air-bike/tests/athlete/${athleteId}`),

  getTest: (testId: string) =>
    fetchApi<AirBikeTest>(`/air-bike/tests/${testId}`),

  createTest: (athleteId: string, data: AirBikeTestCreate) =>
    fetchApi<AirBikeTest>(`/air-bike/tests?athlete_id=${athleteId}`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateTest: (testId: string, data: AirBikeTestUpdate) =>
    fetchApi<AirBikeTest>(`/air-bike/tests/${testId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  deleteTest: (testId: string) =>
    fetchApi<void>(`/air-bike/tests/${testId}`, { method: 'DELETE' }),
};

// Assessments API
export const assessmentApi = {
  listAssessments: (athleteId: string, assessmentType?: string) => {
    const params = new URLSearchParams();
    if (assessmentType) params.set('assessment_type', assessmentType);
    const query = params.toString();
    return fetchApi<MovementAssessmentListItem[]>(
      `/assessments/athlete/${athleteId}${query ? `?${query}` : ''}`
    );
  },

  getAssessment: (id: string) =>
    fetchApi<MovementAssessment>(`/assessments/${id}`),

  createAssessment: (data: MovementAssessmentCreate) =>
    fetchApi<MovementAssessment>('/assessments/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateAssessment: (id: string, data: MovementAssessmentUpdate) =>
    fetchApi<MovementAssessment>(`/assessments/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  deleteAssessment: (id: string) =>
    fetchApi<void>(`/assessments/${id}`, { method: 'DELETE' }),

  uploadPhoto: async (assessmentId: string, file: File, viewType: string): Promise<AssessmentPhoto> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('view_type', viewType);

    const response = await fetch(`${API_BASE}/assessments/${assessmentId}/photos`, {
      method: 'POST',
      credentials: 'include',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
      throw new ApiError(response.status, formatDetail(error?.detail, 'Upload failed'));
    }

    return response.json();
  },

  deletePhoto: (photoId: string) =>
    fetchApi<void>(`/assessments/photos/${photoId}`, { method: 'DELETE' }),
};

// Invitations API
export const invitationsApi = {
  create: (athleteId: string) =>
    fetchApi<InvitationResponse>('/invitations/', {
      method: 'POST',
      body: JSON.stringify({ athlete_id: athleteId }),
    }),

  list: () => fetchApi<InvitationResponse[]>('/invitations/'),

  validate: (code: string) =>
    fetchApi<InvitationValidateResponse>(`/invitations/validate/${code}`),

  revoke: (id: string) =>
    fetchApi<void>(`/invitations/${id}`, { method: 'DELETE' }),
};

// Admin API
export interface AnonymisedAthlete {
  id: string;
  anonymous_name: string;
  gender: string;
  coach_id: string;
}

export interface SharedEvent {
  id: string;
  athlete_id: string;
  event_date: string;
  metrics: Record<string, string | number | undefined>;
}

export const adminApi = {
  listSharedAthletes: (skip = 0, limit = 50) =>
    fetchApi<AnonymisedAthlete[]>(`/admin/shared-athletes?skip=${skip}&limit=${limit}`),

  getSharedEvents: (athleteId: string, skip = 0, limit = 50) =>
    fetchApi<SharedEvent[]>(`/admin/shared-athletes/${athleteId}/events?skip=${skip}&limit=${limit}`),
};

// Consent API
export interface ConsentResponse {
  data_sharing_enabled: boolean;
  consented_at: string | null;
  revoked_at: string | null;
  info_text: string;
}

export const consentApi = {
  get: () => fetchApi<ConsentResponse>('/consent/'),

  update: (dataSharingEnabled: boolean) =>
    fetchApi<ConsentResponse>('/consent/', {
      method: 'PUT',
      body: JSON.stringify({ data_sharing_enabled: dataSharingEnabled }),
    }),
};

// Reports API
export const reportsApi = {
  listForAthlete: (athleteId: string) =>
    fetchApi<TestReportListItem[]>(`/reports/athlete/${athleteId}`),

  get: (reportId: string) =>
    fetchApi<TestReport>(`/reports/${reportId}`),

  create: (data: TestReportCreate) =>
    fetchApi<TestReport>('/reports/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (reportId: string, data: TestReportUpdate) =>
    fetchApi<TestReport>(`/reports/${reportId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  delete: (reportId: string) =>
    fetchApi<void>(`/reports/${reportId}`, { method: 'DELETE' }),
};

// Database Analysis API
export const databaseAnalysisApi = {
  analyze: (request: import('./types').AnalysisRequest) =>
    fetchApi<import('./types').AnalysisResponse>('/database-analysis/analyze', {
      method: 'POST',
      body: JSON.stringify(request),
    }),

  getDomains: () =>
    fetchApi<import('./types').DomainInfo[]>('/database-analysis/domains'),

  getDomainMetrics: (domain: string) =>
    fetchApi<import('./types').DomainMetricsResponse>(`/database-analysis/domain/${domain}/metrics`),
};

// Programs API
export const programsApi = {
  list: (category?: string) => {
    const params = new URLSearchParams();
    if (category) params.set('category', category);
    const query = params.toString();
    return fetchApi<ProgramPackage[]>(`/programs/${query ? `?${query}` : ''}`);
  },

  get: (id: string) => fetchApi<ProgramPackageDetail>(`/programs/${id}`),

  install: (programId: string) =>
    fetchApi<{ message: string }>(`/programs/${programId}/install`, { method: 'POST' }),

  uninstall: (programId: string) =>
    fetchApi<void>(`/programs/${programId}/install`, { method: 'DELETE' }),

  installedTemplates: () =>
    fetchApi<InstalledProgramTemplate[]>('/programs/installed-templates'),

  // Admin endpoints
  create: (data: ProgramPackageCreate) =>
    fetchApi<ProgramPackage>('/programs/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (id: string, data: ProgramPackageUpdate) =>
    fetchApi<ProgramPackage>(`/programs/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    fetchApi<void>(`/programs/${id}`, { method: 'DELETE' }),

  addTemplate: (programId: string, data: ProgramTemplateCreate) =>
    fetchApi<ProgramTemplate>(`/programs/${programId}/templates`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateTemplate: (programId: string, templateId: string, data: ProgramTemplateUpdate) =>
    fetchApi<ProgramTemplate>(`/programs/${programId}/templates/${templateId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  deleteTemplate: (programId: string, templateId: string) =>
    fetchApi<void>(`/programs/${programId}/templates/${templateId}`, { method: 'DELETE' }),

  applyTemplate: (templateId: string, sessionId: string) =>
    fetchApi<ExercisePrescription[]>(
      `/programs/templates/${templateId}/apply?session_id=${sessionId}`,
      { method: 'POST' }
    ),
};

// Air Bike Recordings API
export const airBikeRecordingApi = {
  createRecording: (athleteId: string, data: AirBikeRecordingCreate) =>
    fetchApi<AirBikeRecording>(`/air-bike/recordings?athlete_id=${athleteId}`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  listRecordings: (athleteId: string) =>
    fetchApi<AirBikeRecordingListItem[]>(`/air-bike/recordings/athlete/${athleteId}`),

  getRecording: (recordingId: string) =>
    fetchApi<AirBikeRecording>(`/air-bike/recordings/${recordingId}`),

  deleteRecording: (recordingId: string) =>
    fetchApi<void>(`/air-bike/recordings/${recordingId}`, { method: 'DELETE' }),
};

// Training Blocks API
export const trainingBlocksApi = {
  list: () =>
    fetchApi<TrainingBlock[]>('/training-blocks/'),

  get: (blockId: string) =>
    fetchApi<TrainingBlockDetail>(`/training-blocks/${blockId}`),

  create: (data: TrainingBlockCreate) =>
    fetchApi<TrainingBlock>('/training-blocks/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (blockId: string, data: TrainingBlockUpdate) =>
    fetchApi<TrainingBlock>(`/training-blocks/${blockId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  delete: (blockId: string) =>
    fetchApi<void>(`/training-blocks/${blockId}`, { method: 'DELETE' }),

  createSession: (blockId: string, data: BlockSessionCreate) =>
    fetchApi<BlockSession>(`/training-blocks/${blockId}/sessions`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateSession: (blockId: string, sessionId: string, data: BlockSessionUpdate) =>
    fetchApi<BlockSession>(`/training-blocks/${blockId}/sessions/${sessionId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  deleteSession: (blockId: string, sessionId: string) =>
    fetchApi<void>(`/training-blocks/${blockId}/sessions/${sessionId}`, { method: 'DELETE' }),

  duplicateSession: (blockId: string, sessionId: string, targetWeek: number) =>
    fetchApi<BlockSession>(
      `/training-blocks/${blockId}/sessions/${sessionId}/duplicate?target_week=${targetWeek}`,
      { method: 'POST' }
    ),

  preview: (blockId: string, athleteIds: string[]) =>
    fetchApi<BlockPreviewResponse>(`/training-blocks/${blockId}/preview`, {
      method: 'POST',
      body: JSON.stringify({ athlete_ids: athleteIds }),
    }),

  apply: (blockId: string, data: BlockApplyRequest) =>
    fetchApi<BlockApplyResponse>(`/training-blocks/${blockId}/apply`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  listAthleteMaxes: (athleteId: string) =>
    fetchApi<AthleteMax[]>(`/training-blocks/athlete-maxes/${athleteId}`),

  upsertAthleteMax: (athleteId: string, data: AthleteMaxUpsert) =>
    fetchApi<AthleteMax>(`/training-blocks/athlete-maxes/${athleteId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  deleteAthleteMax: (athleteId: string, exerciseName: string) =>
    fetchApi<void>(
      `/training-blocks/athlete-maxes/${athleteId}/${encodeURIComponent(exerciseName)}`,
      { method: 'DELETE' }
    ),
};

// Programme Forms API
export const programmeFormsApi = {
  list: () =>
    fetchApi<ProgrammeForm[]>('/programme-forms/'),

  get: (id: string) =>
    fetchApi<ProgrammeForm>(`/programme-forms/${id}`),

  create: (data: { form_name: string; description?: string; num_weeks?: number; sessions_per_week?: number; form_data?: ProgrammeFormData }) =>
    fetchApi<ProgrammeForm>('/programme-forms/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (id: string, data: Partial<{ form_name: string; description: string; num_weeks: number; sessions_per_week: number; form_data: ProgrammeFormData }>) =>
    fetchApi<ProgrammeForm>(`/programme-forms/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    fetchApi<void>(`/programme-forms/${id}`, { method: 'DELETE' }),

  apply: (id: string, data: { athlete_ids: string[]; start_date: string }) =>
    fetchApi<{ created_count: number; sessions_per_athlete: number }>(`/programme-forms/${id}/apply`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
};

// ============================================================================
// Boxing Science Combine
// ============================================================================

/**
 * The station operator is standing in front of the boxer, so a stalled save has
 * to fail while they can still re-enter it — not hang until the browser gives up.
 */
const STATION_TIMEOUT_MS = 15000;

function combineFilterQuery(filters?: CombineFilterQuery): string {
  const params = new URLSearchParams();
  if (filters?.weight_category) params.set('weight_category', filters.weight_category);
  if (filters?.age_group) params.set('age_group', filters.age_group);
  if (filters?.club) params.set('club', filters.club);
  if (filters?.squad) params.set('squad', filters.squad);
  const query = params.toString();
  return query ? `?${query}` : '';
}

export const combineApi = {
  listEvents: () => fetchApi<CombineEventListItem[]>('/combine/events'),

  getEvent: (id: string) => fetchApi<CombineEvent>(`/combine/events/${id}`),

  createEvent: (data: CombineEventCreate) =>
    fetchApi<CombineEvent>('/combine/events', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateEvent: (id: string, data: CombineEventUpdate) =>
    fetchApi<CombineEvent>(`/combine/events/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  deleteEvent: (id: string) =>
    fetchApi<void>(`/combine/events/${id}`, { method: 'DELETE' }),

  rotateToken: (id: string) =>
    fetchApi<CombineShareToken>(`/combine/events/${id}/rotate-token`, { method: 'POST' }),

  revokeToken: (id: string) =>
    fetchApi<CombineShareToken>(`/combine/events/${id}/revoke-token`, { method: 'POST' }),

  refreshNorms: (id: string) =>
    fetchApi<CombineEvent>(`/combine/events/${id}/refresh-norms`, { method: 'POST' }),

  sync: (id: string) =>
    fetchApi<CombineLeaderboard>(`/combine/events/${id}/sync`, { method: 'POST' }),

  listParticipants: (id: string) =>
    fetchApi<CombineParticipant[]>(`/combine/events/${id}/participants`),

  /** Always preview with dryRun before importing — it is the duplicate-athlete guard. */
  importRoster: (id: string, rows: CombineRosterRow[], opts?: { dryRun?: boolean; onNameMatch?: 'link' | 'create' }) =>
    fetchApi<CombineRosterResult>(
      `/combine/events/${id}/participants/bulk?dry_run=${opts?.dryRun ? 'true' : 'false'}`,
      {
        method: 'POST',
        body: JSON.stringify({ rows, on_name_match: opts?.onNameMatch ?? 'link' }),
      }
    ),

  updateParticipant: (
    participantId: string,
    // null, not undefined, is how the console clears a text field: JSON.stringify
    // drops undefined and the endpoint patches with exclude_unset, so an undefined
    // club could never be cleared.
    data: Partial<{
      bib: number;
      club: string | null;
      weight_category: string | null;
      age_group: string | null;
      body_mass_kg: number;
      squad: string | null;
      withdrawn: boolean;
    }>
  ) =>
    fetchApi<CombineParticipant>(`/combine/participants/${participantId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  deleteParticipant: (participantId: string) =>
    fetchApi<void>(`/combine/participants/${participantId}`, { method: 'DELETE' }),

  submitAttempt: (eventId: string, data: CombineAttemptSubmit) =>
    fetchApi<CombineAttempt>(
      `/combine/events/${eventId}/attempts`,
      { method: 'POST', body: JSON.stringify(data) },
      { timeoutMs: STATION_TIMEOUT_MS }
    ),

  listAttempts: (eventId: string, opts?: { participantId?: string; station?: CombineStation }) => {
    const params = new URLSearchParams();
    if (opts?.participantId) params.set('participant_id', opts.participantId);
    if (opts?.station) params.set('station', opts.station);
    const query = params.toString();
    return fetchApi<CombineAttempt[]>(
      `/combine/events/${eventId}/attempts${query ? `?${query}` : ''}`,
      undefined,
      { timeoutMs: STATION_TIMEOUT_MS }
    );
  },

  updateAttempt: (attemptId: string, data: { measures?: CombineMeasures; notes?: string }) =>
    fetchApi<CombineAttempt>(`/combine/attempts/${attemptId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  /** Voids by default, keeping the audit trail of what was recorded on the day. */
  deleteAttempt: (attemptId: string, opts?: { hard?: boolean }) =>
    fetchApi<void>(
      `/combine/attempts/${attemptId}?hard=${opts?.hard ? 'true' : 'false'}`,
      { method: 'DELETE' },
      { timeoutMs: STATION_TIMEOUT_MS }
    ),

  stationRoster: (eventId: string, station: CombineStation) =>
    fetchApi<CombineStationRoster>(
      `/combine/events/${eventId}/stations/${station}/roster`,
      undefined,
      { timeoutMs: STATION_TIMEOUT_MS }
    ),

  leaderboard: (eventId: string, filters?: CombineFilterQuery) =>
    fetchApi<CombineLeaderboard>(
      `/combine/events/${eventId}/leaderboard${combineFilterQuery(filters)}`
    ),

  /** Public path used by the kiosk. Sends no credentials and needs no session. */
  publicLeaderboardPath: (token: string, filters?: CombineFilterQuery) =>
    `/api/v1/combine/public/${encodeURIComponent(token)}${combineFilterQuery(filters)}`,
};

export { ApiError };
