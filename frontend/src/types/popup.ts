// 弹窗系统类型定义 - 复刻自寸止

export interface McpRequest {
  id: string
  message: string
  predefined_options?: string[]
  is_markdown?: boolean
}

export interface McpResponse {
  user_input: string | null
  selected_options: string[]
  images: ImageAttachment[]
  metadata: ResponseMetadata
}

export interface ImageAttachment {
  data: string       // base64 编码
  media_type: string  // image/png, image/jpeg 等
  filename: string | null
}

export interface ResponseMetadata {
  timestamp: string
  request_id: string | null
  source: string  // popup_submit, popup_continue, popup_enhance, queue_auto
}

export interface QuickTemplate {
  id: string
  name: string
  content: string
  description?: string
}

export interface ConstraintToggle {
  id: string
  label: string
  description: string
  enabled: boolean
}

export interface AppConfig {
  theme: string
  title: string
  timeout: number
  project: string
  summary: string
  mode?: 'feedback' | 'queue_consume' | 'queue_manager'
  queue_message?: QueueMessage
  queue_count?: number
  auto_consume_delay?: number
}

// ── 队列相关类型 ──

export interface QueueMessage {
  id: string
  content: string
  images: string[]
  created_at: string
  status: 'pending' | 'consumed'
}

export interface QueueSettings {
  auto_consume_delay: number
  show_flash_popup: boolean
  enabled: boolean
}

export interface QueueState {
  queue: QueueMessage[]
  count: number
}
