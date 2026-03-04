<script setup lang="ts">
// McpPopup - 主弹窗组件，复刻寸止布局
// Header (固定) + Content + Input (可滚动) + Actions (固定底部)
import type { McpRequest, McpResponse } from '../types/popup'
import { useMessage } from 'naive-ui'
import { computed, onMounted, onUnmounted, ref } from 'vue'

import PopupActions from './PopupActions.vue'
import PopupContent from './PopupContent.vue'
import PopupHeader from './PopupHeader.vue'
import PopupInput from './PopupInput.vue'

interface Props {
  request: McpRequest | null
  currentTheme?: string
  sessionId?: string  // 窗口唯一会话ID
}

interface Emits {
  response: [response: McpResponse]
  cancel: []
  themeChange: [theme: string]
}

const props = withDefaults(defineProps<Props>(), {
  currentTheme: 'light',
  sessionId: '',
})

const emit = defineEmits<Emits>()
const message = useMessage()

// 状态
const loading = ref(false)
const submitting = ref(false)
const selectedOptions = ref<string[]>([])
const userInput = ref('')
const draggedImages = ref<string[]>([])
const inputRef = ref()

// 计算属性
const isVisible = computed(() => !!props.request)
const hasOptions = computed(() => (props.request?.predefined_options?.length ?? 0) > 0)
const canSubmit = computed(() => {
  if (hasOptions.value) {
    return selectedOptions.value.length > 0 || userInput.value.trim().length > 0 || draggedImages.value.length > 0
  }
  return userInput.value.trim().length > 0 || draggedImages.value.length > 0
})

const inputStatusText = computed(() => inputRef.value?.statusText || '等待输入...')

// 处理输入更新
function handleInputUpdate(data: { userInput: string; selectedOptions: string[]; draggedImages: string[] }) {
  userInput.value = data.userInput
  selectedOptions.value = data.selectedOptions
  draggedImages.value = data.draggedImages
}

function handleImageAdd(_image: string) {
  // PopupInput内部处理
}

function handleImageRemove(index: number) {
  draggedImages.value.splice(index, 1)
}

// 提交
async function handleSubmit() {
  if (!canSubmit.value || submitting.value) return
  submitting.value = true

  try {
    const response: McpResponse = {
      user_input: userInput.value.trim() || null,
      selected_options: [...selectedOptions.value],
      images: draggedImages.value.map((data, i) => ({
        data,
        media_type: 'image/png',
        filename: `image_${i + 1}.png`,
      })),
      metadata: {
        timestamp: new Date().toISOString(),
        request_id: props.request?.id || null,
        source: 'popup_submit',
      },
    }

    // 发送到后端
    await fetch('/api/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(response),
    })

    emit('response', response)
    message.success('反馈已提交')
  } catch (error) {
    console.error('提交失败:', error)
    message.error('提交失败，请重试')
  } finally {
    submitting.value = false
  }
}

// 继续
async function handleContinue() {
  if (submitting.value) return
  submitting.value = true

  try {
    const response: McpResponse = {
      user_input: '请按照最佳实践继续',
      selected_options: [],
      images: [],
      metadata: {
        timestamp: new Date().toISOString(),
        request_id: props.request?.id || null,
        source: 'popup_continue',
      },
    }

    await fetch('/api/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(response),
    })

    emit('response', response)
  } catch (error) {
    console.error('继续请求失败:', error)
    message.error('请求失败')
  } finally {
    submitting.value = false
  }
}

// 增强
async function handleEnhance() {
  if (submitting.value) return
  submitting.value = true

  try {
    const enhancePrompt = `Use the following prompt to optimize and enhance the context of the content in 《》, and return the enhanced result by calling the tool after completion.

Here is my original instruction:
《${userInput.value.trim()}》`

    const response: McpResponse = {
      user_input: enhancePrompt,
      selected_options: [],
      images: [],
      metadata: {
        timestamp: new Date().toISOString(),
        request_id: props.request?.id || null,
        source: 'popup_enhance',
      },
    }

    await fetch('/api/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(response),
    })

    emit('response', response)
    message.success('增强请求已发送')
  } catch (error) {
    console.error('增强失败:', error)
    message.error('增强失败')
  } finally {
    submitting.value = false
  }
}

// 引用消息
function handleQuoteMessage(messageContent: string) {
  if (inputRef.value) {
    inputRef.value.handleQuoteMessage(messageContent)
  }
}

// 加入队列
async function handleAddToQueue() {
  if (!canSubmit.value || submitting.value) return

  const content = userInput.value.trim()
  if (!content) {
    message.warning('请输入消息内容')
    return
  }

  try {
    const res = await fetch('/api/queue', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        content,
        images: draggedImages.value,
      }),
    })

    if (res.ok) {
      const data = await res.json()
      message.success(`已加入队列 (${data.count}条待发送)`)
      // 清空输入
      userInput.value = ''
      draggedImages.value = []
      selectedOptions.value = []
      if (inputRef.value) inputRef.value.reset()
    } else {
      const err = await res.json()
      message.error(err.error || '加入队列失败')
    }
  } catch (error) {
    console.error('加入队列失败:', error)
    message.error('加入队列失败')
  }
}

// 主题切换
function handleThemeChange(theme: string) {
  emit('themeChange', theme)
}

// 全局快捷键
function handleGlobalKeydown(e: KeyboardEvent) {
  if (e.ctrlKey && e.key === 'Enter') {
    e.preventDefault()
    handleSubmit()
  }
  if (e.altKey && e.key === 'e') {
    e.preventDefault()
    handleEnhance()
  }
  if (e.altKey && e.key === 'c') {
    e.preventDefault()
    handleContinue()
  }
  if (e.altKey && e.key === 'q') {
    e.preventDefault()
    handleAddToQueue()
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleGlobalKeydown)
})
onUnmounted(() => {
  window.removeEventListener('keydown', handleGlobalKeydown)
})
</script>

<template>
  <div v-if="isVisible" class="mcp-popup" :class="{ dark: currentTheme === 'dark' }">
    <!-- 头部 - 固定 -->
    <div class="popup-header-wrap">
      <PopupHeader
        :current-theme="currentTheme"
        :title="sessionId ? `柠檬酱帮你阻止了会话结束 [${sessionId.slice(-8)}]` : '柠檬酱帮你阻止了会话结束'"
        @theme-change="handleThemeChange"
      >
        <template #extra>
          <slot name="header-extra"></slot>
        </template>
      </PopupHeader>
    </div>

    <!-- 内容区域 - 可滚动 -->
    <div class="popup-scroll-area">
      <!-- AI消息卡片 -->
      <div class="content-card">
        <PopupContent
          :request="request"
          :loading="loading"
          :current-theme="currentTheme"
          @quote-message="handleQuoteMessage"
        />
      </div>

      <!-- 输入/选项区域 -->
      <div class="input-area">
        <PopupInput
          ref="inputRef"
          :request="request"
          :loading="loading"
          :submitting="submitting"
          :current-theme="currentTheme"
          @update="handleInputUpdate"
          @image-add="handleImageAdd"
          @image-remove="handleImageRemove"
        />
      </div>
    </div>

    <!-- 底部操作栏 - 固定 -->
    <div class="popup-actions-wrap">
      <PopupActions
        :request="request"
        :loading="loading"
        :submitting="submitting"
        :can-submit="canSubmit"
        :continue-reply-enabled="true"
        :input-status-text="inputStatusText"
        :current-theme="currentTheme"
        @submit="handleSubmit"
        @continue="handleContinue"
        @enhance="handleEnhance"
        @add-to-queue="handleAddToQueue"
      />
    </div>
  </div>
</template>

<style scoped>
.mcp-popup {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100vh;
  background: #f0f2f5;
  color: #303133;
  overflow: hidden;
}
.mcp-popup.dark {
  background: #141414;
  color: #e0e0e0;
}

.popup-header-wrap {
  flex-shrink: 0;
  z-index: 10;
}

.popup-scroll-area {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 0;
}

/* 自定义滚动条 */
.popup-scroll-area::-webkit-scrollbar {
  width: 6px;
}
.popup-scroll-area::-webkit-scrollbar-track {
  background: transparent;
}
.popup-scroll-area::-webkit-scrollbar-thumb {
  background: #c0c4cc;
  border-radius: 3px;
}
.popup-scroll-area::-webkit-scrollbar-thumb:hover {
  background: #909399;
}
.dark .popup-scroll-area::-webkit-scrollbar-thumb {
  background: #555;
}

.content-card {
  margin: 8px;
  padding: 16px;
  background: #ffffff;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.dark .content-card {
  background: #1e1e1e;
}

.input-area {
  padding: 0 16px 12px;
}

.popup-actions-wrap {
  flex-shrink: 0;
  z-index: 10;
}
</style>
