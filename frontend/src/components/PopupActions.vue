<script setup lang="ts">
// PopupActions - 复刻寸止底部操作栏
// 连接状态 + 增强/继续/加入队列/发送按钮
import type { McpRequest } from '../types/popup'
import { NButton, NSpace, NTooltip, NBadge } from 'naive-ui'
import { computed, onMounted, ref } from 'vue'

interface Props {
  request: McpRequest | null
  loading?: boolean
  submitting?: boolean
  canSubmit?: boolean
  connectionStatus?: string
  continueReplyEnabled?: boolean
  inputStatusText?: string
  currentTheme?: string
}

interface Emits {
  submit: []
  continue: []
  enhance: []
  addToQueue: []
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  submitting: false,
  canSubmit: false,
  connectionStatus: '已连接',
  continueReplyEnabled: true,
  inputStatusText: '',
  currentTheme: 'light',
})

const emit = defineEmits<Emits>()

// 队列消息数
const queueCount = ref(0)

const statusText = computed(() => {
  if (props.canSubmit) return 'Ctrl+Enter 快速发送'
  if (props.inputStatusText && props.inputStatusText !== '等待输入...') {
    return props.inputStatusText
  }
  if (props.request?.predefined_options) return '选择选项或输入文本'
  return '请输入内容'
})

function handleSubmit() {
  if (props.canSubmit && !props.submitting) emit('submit')
}
function handleContinue() {
  if (!props.submitting) emit('continue')
}
function handleEnhance() {
  if (!props.submitting) emit('enhance')
}
function handleAddToQueue() {
  if (props.canSubmit && !props.submitting) emit('addToQueue')
}

// 获取队列数量
async function fetchQueueCount() {
  try {
    const res = await fetch('/api/queue/count')
    if (res.ok) {
      const data = await res.json()
      queueCount.value = data.count || 0
    }
  } catch {
    // 忽略
  }
}

// Ctrl+Enter 快捷键
function handleKeydown(e: KeyboardEvent) {
  if (e.ctrlKey && e.key === 'Enter') {
    e.preventDefault()
    handleSubmit()
  }
}

onMounted(() => {
  fetchQueueCount()
})
</script>

<template>
  <div
    class="popup-actions"
    :class="{ dark: $attrs.currentTheme === 'dark' }"
    @keydown="handleKeydown"
  >
    <div v-if="!loading" class="actions-inner">
      <!-- 左侧状态 -->
      <div class="status-area">
        <div class="status-indicator">
          <div class="status-dot-sm"></div>
          <span class="status-text">{{ connectionStatus }}</span>
          <span class="status-sep">|</span>
          <span class="status-hint">{{ statusText }}</span>
        </div>
      </div>

      <!-- 右侧按钮 -->
      <div class="buttons-area">
        <n-space size="small">
          <!-- 加入队列按钮 -->
          <n-tooltip trigger="hover" placement="top">
            <template #trigger>
              <n-badge :value="queueCount" :show="queueCount > 0" :offset="[-4, 0]">
                <n-button
                  :disabled="!canSubmit || submitting"
                  size="medium"
                  type="warning"
                  quaternary
                  @click="handleAddToQueue"
                >
                  <template #icon>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/>
                      <line x1="8" y1="18" x2="21" y2="18"/>
                      <line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/>
                      <line x1="3" y1="18" x2="3.01" y2="18"/>
                    </svg>
                  </template>
                  队列
                </n-button>
              </n-badge>
            </template>
            Alt+Q 加入发送队列（不立即发送）
          </n-tooltip>

          <!-- 增强按钮 -->
          <n-tooltip trigger="hover" placement="top">
            <template #trigger>
              <n-button
                :disabled="!canSubmit || submitting"
                size="medium"
                type="info"
                @click="handleEnhance"
              >
                <template #icon>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M15 4V2M15 16v-2M8 9h2M20 9h2M17.8 11.8L19 13M17.8 6.2L19 5M12.2 11.8L11 13M12.2 6.2L11 5M15 9a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"/>
                  </svg>
                </template>
                增强
              </n-button>
            </template>
            Alt+E 增强提示词
          </n-tooltip>

          <!-- 继续按钮 -->
          <n-tooltip v-if="continueReplyEnabled" trigger="hover" placement="top">
            <template #trigger>
              <n-button
                :disabled="submitting"
                :loading="submitting"
                size="medium"
                type="default"
                @click="handleContinue"
              >
                <template #icon>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polygon points="5 3 19 12 5 21 5 3"/>
                  </svg>
                </template>
                继续
              </n-button>
            </template>
            Alt+C 继续执行
          </n-tooltip>

          <!-- 发送按钮 -->
          <n-tooltip trigger="hover" placement="top">
            <template #trigger>
              <n-button
                type="primary"
                :disabled="!canSubmit || submitting"
                :loading="submitting"
                size="medium"
                @click="handleSubmit"
              >
                <template #icon>
                  <svg v-if="!submitting" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
                  </svg>
                </template>
                {{ submitting ? '发送中...' : '发送' }}
              </n-button>
            </template>
            Ctrl+Enter 快速发送
          </n-tooltip>
        </n-space>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-else class="actions-loading">
      <span>加载中...</span>
    </div>
  </div>
</template>

<style scoped>
.popup-actions {
  padding: 10px 16px;
  background: #fafafa;
  border-top: 1px solid #e4e7ed;
  min-height: 52px;
  user-select: none;
}
.dark .popup-actions,
.popup-actions.dark {
  background: #1e1e1e;
  border-top-color: #333;
}

.actions-inner {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.status-area {
  flex: 1;
  min-width: 0;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: #909399;
}

.status-dot-sm {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #52c41a;
  flex-shrink: 0;
}

.status-text {
  font-weight: 500;
  color: #606266;
}
.dark .status-text {
  color: #aaa;
}

.status-sep {
  opacity: 0.4;
}

.status-hint {
  opacity: 0.6;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.buttons-area {
  flex-shrink: 0;
}

.actions-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #909399;
  font-size: 12px;
}
</style>
