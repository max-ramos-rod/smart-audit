// Mock data seguindo a estrutura real do Smart Audit
import type { 
  Form, 
  FormVersion, 
  FormField, 
  Submission, 
  DraftAnswers,
  Attachment,
  FieldType,
  InspectionProgress
} from './types'

// Helper para gerar UUIDs
const uuid = () => crypto.randomUUID()

// =========================================
// MOCK FORM FIELDS
// =========================================

const createField = (
  versionId: string,
  key: string,
  label: string,
  type: FieldType,
  position: number,
  config: FormField['config_json'] = {},
  required = true
): FormField => ({
  id: uuid(),
  form_version_id: versionId,
  key,
  label,
  field_type: type,
  required,
  position,
  config_json: config,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
})

// =========================================
// MOCK FORM - Checklist de Segurança
// =========================================

const formId = uuid()
const versionId = uuid()
const companyId = uuid()
const userId = uuid()

const mockFields: FormField[] = [
  // Seção 1: EPIs
  createField(versionId, '__section_1__', 'Equipamentos de Proteção Individual', 'section', 1),
  createField(versionId, 'capacete_uso', 'Colaborador está utilizando capacete de segurança?', 'boolean', 2, { weight: 3, allow_na: false }),
  createField(versionId, 'capacete_estado', 'Capacete em bom estado de conservação?', 'boolean', 3, { weight: 2, allow_na: false }),
  createField(versionId, 'oculos_uso', 'Óculos de proteção em uso?', 'boolean', 4, { weight: 2, allow_na: true }),
  createField(versionId, 'luvas_uso', 'Luvas de proteção adequadas ao trabalho?', 'boolean', 5, { weight: 2, allow_na: true }),
  createField(versionId, 'calcado_seguranca', 'Calçado de segurança apropriado?', 'boolean', 6, { weight: 3 }),
  createField(versionId, 'epi_observacao', 'Observações sobre EPIs', 'text', 7, {}, false),
  
  // Seção 2: Área de Trabalho
  createField(versionId, '__section_2__', 'Condições da Área de Trabalho', 'section', 8),
  createField(versionId, 'area_limpa', 'Área de trabalho limpa e organizada?', 'boolean', 9, { weight: 2 }),
  createField(versionId, 'sinalizacao_ok', 'Sinalização de segurança visível e adequada?', 'boolean', 10, { weight: 3 }),
  createField(versionId, 'iluminacao_ok', 'Iluminação adequada para a atividade?', 'boolean', 11, { weight: 2 }),
  createField(versionId, 'ventilacao_ok', 'Ventilação adequada no ambiente?', 'boolean', 12, { weight: 1, allow_na: true }),
  createField(versionId, 'saida_emergencia', 'Saídas de emergência desobstruídas?', 'boolean', 13, { weight: 3 }),
  createField(versionId, 'extintor_acessivel', 'Extintores acessíveis e dentro da validade?', 'boolean', 14, { weight: 3 }),
  
  // Seção 3: Máquinas e Equipamentos
  createField(versionId, '__section_3__', 'Máquinas e Equipamentos', 'section', 15),
  createField(versionId, 'maquina_protecao', 'Máquinas possuem proteções adequadas?', 'boolean', 16, { weight: 3 }),
  createField(versionId, 'parada_emergencia', 'Dispositivos de parada de emergência funcionando?', 'boolean', 17, { weight: 3 }),
  createField(versionId, 'manutencao_dia', 'Manutenção preventiva em dia?', 'boolean', 18, { weight: 2, allow_na: true }),
  createField(versionId, 'operador_treinado', 'Operador possui treinamento documentado?', 'boolean', 19, { weight: 2 }),
  createField(versionId, 'tipo_equipamento', 'Tipo de equipamento inspecionado', 'select', 20, { 
    options: ['Empilhadeira', 'Ponte Rolante', 'Prensa', 'Torno', 'Fresadora', 'Outro'] 
  }),
  createField(versionId, 'numero_patrimonio', 'Número do patrimônio', 'text', 21),
  
  // Seção 4: Trabalho em Altura (condicional)
  createField(versionId, '__section_4__', 'Trabalho em Altura', 'section', 22),
  createField(versionId, 'trabalho_altura', 'Há trabalho em altura nesta atividade?', 'boolean', 23, { weight: 1 }),
  createField(versionId, 'cinto_seguranca', 'Cinto de segurança tipo paraquedista em uso?', 'boolean', 24, { 
    weight: 3, 
    visible_if: { field_key: 'trabalho_altura', operator: 'eq', value: true } 
  }),
  createField(versionId, 'talabarte_duplo', 'Talabarte duplo conectado a ponto de ancoragem?', 'boolean', 25, { 
    weight: 3, 
    visible_if: { field_key: 'trabalho_altura', operator: 'eq', value: true } 
  }),
  createField(versionId, 'andaime_montado', 'Andaime montado conforme NR-18?', 'boolean', 26, { 
    weight: 3, 
    allow_na: true,
    visible_if: { field_key: 'trabalho_altura', operator: 'eq', value: true } 
  }),
  createField(versionId, 'altura_metros', 'Altura aproximada do trabalho (metros)', 'number', 27, {
    visible_if: { field_key: 'trabalho_altura', operator: 'eq', value: true }
  }),
  
  // Seção 5: Evidências
  createField(versionId, '__section_5__', 'Registro Fotográfico', 'section', 28),
  createField(versionId, 'foto_geral', 'Foto geral da área inspecionada', 'photo', 29, {}, false),
  createField(versionId, 'evidencias_nc', 'Evidências de não-conformidades encontradas', 'evidence', 30, {}, false),
  
  // Seção 6: Finalização
  createField(versionId, '__section_6__', 'Finalização', 'section', 31),
  createField(versionId, 'data_inspecao', 'Data da inspeção', 'date', 32),
  createField(versionId, 'parecer_geral', 'Parecer geral sobre as condições de segurança', 'text', 33),
]

export const mockFormVersion: FormVersion = {
  id: versionId,
  form_id: formId,
  version: 1,
  status: 'published',
  published_at: new Date().toISOString(),
  created_by: userId,
  fields: mockFields,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
}

export const mockForm: Form = {
  id: formId,
  company_id: companyId,
  name: 'Checklist de Segurança do Trabalho',
  description: 'Inspeção de rotina para verificação das condições de segurança conforme NR-12 e NR-35',
  is_active: true,
  created_by: userId,
  current_version: mockFormVersion,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
}

// =========================================
// MOCK SUBMISSION (em andamento)
// =========================================

export const mockSubmission: Submission = {
  id: uuid(),
  company_id: companyId,
  form_version_id: versionId,
  created_by: userId,
  status: 'in_progress',
  score: null,
  started_at: new Date().toISOString(),
  finished_at: null,
  answers_json: {},
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
}

// Respostas parciais para demonstração
export const mockDraftAnswers: DraftAnswers = {
  'capacete_uso': true,
  'capacete_estado': true,
  'oculos_uso': true,
  'luvas_uso': 'na',
  'calcado_seguranca': true,
  'area_limpa': true,
  'sinalizacao_ok': false,
  'trabalho_altura': true,
}

// =========================================
// MOCK ATTACHMENTS
// =========================================

export const mockAttachments: Attachment[] = [
  {
    id: uuid(),
    submission_value_id: uuid(),
    field_key: 'sinalizacao_ok',
    file_url: '/uploads/sinalizacao_danificada.jpg',
    thumbnail_url: '/uploads/thumb_sinalizacao_danificada.jpg',
    mime_type: 'image/jpeg',
    file_size: 245000,
    uploaded_by: userId,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  }
]

// =========================================
// HELPERS
// =========================================

// Extrai seções do formulário para navegação rápida
export function extractSections(fields: FormField[]): { id: string; label: string; position: number }[] {
  return fields
    .filter(f => f.field_type === 'section')
    .map(f => ({
      id: f.id,
      label: f.label,
      position: f.position,
    }))
}

// Filtra campos visíveis baseado nas respostas atuais
export function getVisibleFields(fields: FormField[], answers: DraftAnswers): FormField[] {
  return fields.filter(field => {
    const visibleIf = field.config_json.visible_if
    if (!visibleIf) return true
    
    const dependentValue = answers[visibleIf.field_key]
    const expectedValue = visibleIf.value
    
    if (visibleIf.operator === 'eq') {
      return dependentValue === expectedValue
    } else {
      return dependentValue !== expectedValue
    }
  })
}

// Calcula progresso da inspeção
export function calculateProgress(fields: FormField[], answers: DraftAnswers): InspectionProgress {
  const visibleFields = getVisibleFields(fields, answers)
  const answerableFields = visibleFields.filter(f => f.field_type !== 'section')
  
  let compliant = 0
  let nonCompliant = 0
  let na = 0
  let answered = 0
  
  for (const field of answerableFields) {
    const value = answers[field.key]
    if (value !== undefined && value !== null) {
      answered++
      if (field.field_type === 'boolean') {
        if (value === true) compliant++
        else if (value === false) nonCompliant++
        else if (value === 'na') na++
      }
    }
  }
  
  return {
    total: answerableFields.length,
    answered,
    compliant,
    nonCompliant,
    na,
    percentage: answerableFields.length > 0 
      ? Math.round((answered / answerableFields.length) * 100) 
      : 0,
  }
}

// Calcula score ponderado (conforme Arquitetura_Smart_Audit.md)
export function calculateWeightedScore(fields: FormField[], answers: DraftAnswers): number | null {
  const visibleFields = getVisibleFields(fields, answers)
  const booleanFields = visibleFields.filter(f => f.field_type === 'boolean')
  
  let weightedConformes = 0
  let weightedTotal = 0
  
  for (const field of booleanFields) {
    const value = answers[field.key]
    const weight = field.config_json.weight ?? 1
    
    // N/A e sem resposta não entram no denominador
    if (value === true) {
      weightedConformes += weight
      weightedTotal += weight
    } else if (value === false) {
      weightedTotal += weight
    }
    // 'na' e undefined são ignorados
  }
  
  if (weightedTotal === 0) return null
  return Math.round((weightedConformes / weightedTotal) * 100)
}

// Retorna o status visual de um campo
export function getFieldStatus(field: FormField, answers: DraftAnswers): 'pending' | 'compliant' | 'non_compliant' | 'na' {
  const value = answers[field.key]
  
  if (value === undefined || value === null) return 'pending'
  if (value === 'na') return 'na'
  if (field.field_type === 'boolean') {
    return value === true ? 'compliant' : 'non_compliant'
  }
  return 'compliant' // Outros tipos com valor são considerados respondidos
}
