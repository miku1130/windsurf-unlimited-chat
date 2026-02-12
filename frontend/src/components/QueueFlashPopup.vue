<script setup lang="ts">
// QueueFlashPopup - 队列自动消费快闪弹窗
// 倒计时进度条 + 消息预览 + 取消按钮

import type { QueueMessage } from '../types/popup'
import { NButton, NProgress } from 'naive-ui'
import { computed, onMounted, onUnmounted, ref } from 'vue'

interface Props {
  message: QueueMessage | null
  queueCount: number
  delay: number  // 自动发送延迟（秒）
  currentTheme?: string
}

interface Emits {
  cancel: []
  submitted: []
}

const props = withDefaults(defineProps<Props>(), {
  currentTheme: 'light',
})

const emit = defineEmits<Emits>()

// 倒计时状态
const remaining = ref(props.delay * 1000)  // 毫秒
const totalMs = props.delay * 1000
const timer = ref<number | null>(null)
const cancelled = ref(false)

// 进度百分比 (100 -> 0)
const progress = computed(() => Math.round((remaining.value / totalMs) * 100))
const remainingSeconds = computed(() => Math.ceil(remaining.value / 1000))

// 倒计时逻辑
function startCountdown() {
  const interval = 50  // 50ms 更新一次，更流畅
  timer.value = window.setInterval(() => {
    remaining.value -= interval
    if (remaining.value <= 0) {
      remaining.value = 0
      stopCountdown()
      // 自动提交
      autoSubmit()
    }
  }, interval)
}

function stopCountdown() {
  if (timer.value) {
    clearInterval(timer.value)
    timer.value = null
  }
}

async function autoSubmit() {
  if (cancelled.value) return

  try {
    const response = {
      user_input: props.message?.content || '',
      selected_options: [],
      images: (props.message?.images || []).map((data: string, i: number) => ({
        data,
        media_type: 'image/png',
        filename: `queue_image_${i + 1}.png`,
      })),
      metadata: {
        timestamp: new Date().toISOString(),
        request_id: null,
        source: 'queue_auto',
        queue_msg_id: props.message?.id || null,
      },
    }

    await fetch('/api/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(response),
    })

    emit('submitted')
  } catch (e) {
    console.error('自动提交失败:', e)
  }
}

function handleCancel() {
  cancelled.value = true
  stopCountdown()

  // 通知后端取消
  fetch('/api/queue/cancel', { method: 'POST' }).catch(() => {})

  emit('cancel')
}

onMounted(() => {
  startCountdown()
})

onUnmounted(() => {
  stopCountdown()
})
</script>

<template>
  <div class="flash-popup" :class="{ dark: currentTheme === 'dark' }">
    <!-- 头部 -->
    <div class="flash-header">
      <div class="flash-title-area">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#1890ff" stroke-width="2">
          <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
        </svg>
        <h3 class="flash-title">队列自动发送中</h3>
      </div>
      <span class="flash-count">{{ queueCount }} 条待发送</span>
    </div>

    <!-- 进度条 -->
    <div class="flash-progress">
      <n-progress
        type="line"
        :percentage="progress"
        :show-indicator="false"
        :height="4"
        :color="progress > 30 ? '#1890ff' : '#ff4d4f'"
        rail-color="rgba(0,0,0,0.06)"
      />
      <span class="countdown-text">{{ remainingSeconds }}秒后自动发送</span>
    </div>

    <!-- 消息预览 -->
    <div class="flash-content" v-if="message">
      <div class="message-label">即将发送:</div>
      <div class="message-preview">{{ message.content }}</div>
    </div>

    <!-- 操作按钮 -->
    <div class="flash-actions">
      <n-button
        size="medium"
        type="error"
        @click="handleCancel"
        :disabled="cancelled"
      >
        取消自动发送
      </n-button>
      <span class="action-hint">取消后将进入正常输入模式</span>
    </div>
  </div>
</template>

<style scoped>
.flash-popup {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100vh;
  background: #f0f2f5;
  color: #303133;
  padding: 20px;
  box-sizing: border-box;
}
.flash-popup.dark {
  background: #141414;
  color: #e0e0e0;
}

.flash-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.flash-title-area {
  display: flex;
  align-items: center;
  gap: 8px;
}
.flash-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
}
.flash-count {
  font-size: 13px;
  color: #1890ff;
  background: #e6f7ff;
  padding: 2px 10px;
  border-radius: 12px;
}
.dark .flash-count {
  background: #1a3a5c;
}

.flash-progress {
  margin-bottom: 20px;
}
.countdown-text {
  display: block;
  text-align: center;
  font-size: 13px;
  color: #909399;
  margin-top: 6px;
}

.flash-content {
  flex: 1;
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
  border: 1px solid #e4e7ed;
  overflow-y: auto;
}
.dark .flash-content {
  background: #1e1e1e;
  border-color: #333;
}
.message-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
}
.message-preview {
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
}

.flash-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}
.action-hint {
  font-size: 11px;
  color: #909399;
}
</style>
