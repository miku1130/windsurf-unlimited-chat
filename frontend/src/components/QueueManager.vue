<script setup lang="ts">
// QueueManager - 队列管理页面
// 完整的消息队列管理：添加/编辑/删除/排序/清空

import type { QueueMessage, QueueSettings } from '../types/popup'
import { NButton, NInput, NSlider, NSwitch, NEmpty, NSpace, NTag, useMessage, NPopconfirm } from 'naive-ui'
import { computed, onMounted, onUnmounted, ref } from 'vue'

interface Props {
  currentTheme?: string
}

interface Emits {
  back: []
  themeChange: [theme: string]
}

const props = withDefaults(defineProps<Props>(), {
  currentTheme: 'light',
})

const emit = defineEmits<Emits>()
const message = useMessage()

// 状态
const queue = ref<QueueMessage[]>([])
const queueCount = ref(0)
const settings = ref<QueueSettings>({
  auto_consume_delay: 3,
  show_flash_popup: true,
  enabled: true,
})
const newMessageContent = ref('')
const editingId = ref<string | null>(null)
const editContent = ref('')
const loading = ref(false)
const pollTimer = ref<number | null>(null)

// 拖拽状态
const dragIndex = ref<number | null>(null)
const dragOverIndex = ref<number | null>(null)

// 计算属性
const hasMessages = computed(() => queue.value.length > 0)

// ── API 调用 ──

async function fetchQueue() {
  try {
    const res = await fetch('/api/queue')
    if (res.ok) {
      const data = await res.json()
      queue.value = data.queue || []
      queueCount.value = data.count || 0
    }
  } catch (e) {
    console.error('获取队列失败:', e)
  }
}

async function fetchSettings() {
  try {
    const res = await fetch('/api/queue/settings')
    if (res.ok) {
      const data = await res.json()
      settings.value = { ...settings.value, ...data }
    }
  } catch (e) {
    console.error('获取队列设置失败:', e)
  }
}

async function addMessage() {
  const content = newMessageContent.value.trim()
  if (!content) return

  loading.value = true
  try {
    const res = await fetch('/api/queue', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, images: [] }),
    })
    if (res.ok) {
      newMessageContent.value = ''
      message.success('消息已加入队列')
      await fetchQueue()
    } else {
      const err = await res.json()
      message.error(err.error || '添加失败')
    }
  } catch (e) {
    message.error('添加失败')
  } finally {
    loading.value = false
  }
}

async function removeMessage(msgId: string) {
  try {
    const res = await fetch(`/api/queue/delete/${msgId}`, { method: 'POST' })
    if (res.ok) {
      message.success('已删除')
      await fetchQueue()
    }
  } catch (e) {
    message.error('删除失败')
  }
}

async function clearQueue() {
  try {
    const res = await fetch('/api/queue/clear', { method: 'POST' })
    if (res.ok) {
      message.success('队列已清空')
      await fetchQueue()
    }
  } catch (e) {
    message.error('清空失败')
  }
}

function startEdit(msg: QueueMessage) {
  editingId.value = msg.id
  editContent.value = msg.content
}

function cancelEdit() {
  editingId.value = null
  editContent.value = ''
}

async function saveEdit(msgId: string) {
  const content = editContent.value.trim()
  if (!content) return

  try {
    const res = await fetch(`/api/queue/update/${msgId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    })
    if (res.ok) {
      editingId.value = null
      editContent.value = ''
      message.success('已更新')
      await fetchQueue()
    }
  } catch (e) {
    message.error('更新失败')
  }
}

async function saveSettings() {
  try {
    const res = await fetch('/api/queue/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings.value),
    })
    if (res.ok) {
      message.success('设置已保存')
    }
  } catch (e) {
    message.error('保存设置失败')
  }
}

// ── 拖拽排序 ──

function handleDragStart(index: number) {
  dragIndex.value = index
}

function handleDragOver(e: DragEvent, index: number) {
  e.preventDefault()
  dragOverIndex.value = index
}

function handleDragLeave() {
  dragOverIndex.value = null
}

async function handleDrop(index: number) {
  if (dragIndex.value === null || dragIndex.value === index) {
    dragIndex.value = null
    dragOverIndex.value = null
    return
  }

  // 本地重排
  const items = [...queue.value]
  const [moved] = items.splice(dragIndex.value, 1)
  items.splice(index, 0, moved)
  queue.value = items

  dragIndex.value = null
  dragOverIndex.value = null

  // 同步到后端
  try {
    await fetch('/api/queue/reorder', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ids: items.map(m => m.id) }),
    })
  } catch (e) {
    console.error('排序同步失败:', e)
    await fetchQueue() // 回退
  }
}

// 快捷键：Ctrl+Enter 添加消息
function handleKeydown(e: KeyboardEvent) {
  if (e.ctrlKey && e.key === 'Enter') {
    e.preventDefault()
    addMessage()
  }
}

// 格式化时间
function formatTime(isoStr: string): string {
  try {
    const d = new Date(isoStr)
    return d.toLocaleString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch {
    return isoStr
  }
}

// 定时轮询（队列管理器模式下，保持数据同步）
function startPolling() {
  pollTimer.value = window.setInterval(fetchQueue, 3000)
}

function stopPolling() {
  if (pollTimer.value) {
    clearInterval(pollTimer.value)
    pollTimer.value = null
  }
}

onMounted(async () => {
  await Promise.all([fetchQueue(), fetchSettings()])
  startPolling()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<template>
  <div class="queue-manager" :class="{ dark: currentTheme === 'dark' }">
    <!-- 头部 -->
    <div class="qm-header">
      <div class="qm-header-left">
        <button class="back-btn" @click="emit('back')" title="返回">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="15 18 9 12 15 6"/>
          </svg>
        </button>
        <h2 class="qm-title">消息队列管理</h2>
        <n-tag v-if="hasMessages" type="info" size="small" round>
          {{ queueCount }} 条待发送
        </n-tag>
      </div>
      <div class="qm-header-right">
        <n-popconfirm v-if="hasMessages" @positive-click="clearQueue">
          <template #trigger>
            <n-button size="small" type="error" quaternary>清空队列</n-button>
          </template>
          确定清空所有 {{ queueCount }} 条消息吗？
        </n-popconfirm>
      </div>
    </div>

    <!-- 添加消息区域 -->
    <div class="qm-add-section">
      <h4 class="section-label">添加消息到队列</h4>
      <div class="add-input-wrap">
        <n-input
          v-model:value="newMessageContent"
          type="textarea"
          placeholder="输入消息内容，将在下次弹窗时自动发送... (Ctrl+Enter 添加)"
          :autosize="{ minRows: 2, maxRows: 5 }"
          @keydown="handleKeydown"
        />
        <n-button
          type="primary"
          :disabled="!newMessageContent.trim()"
          :loading="loading"
          @click="addMessage"
          class="add-btn"
        >
          加入队列
        </n-button>
      </div>
    </div>

    <!-- 队列列表 -->
    <div class="qm-list-section">
      <h4 class="section-label">
        待发送消息
        <span class="hint">(拖拽排序，从上到下依次发送)</span>
      </h4>

      <n-empty v-if="!hasMessages" description="队列为空，暂无待发送消息" class="empty-state" />

      <div v-else class="queue-list">
        <div
          v-for="(msg, index) in queue"
          :key="msg.id"
          class="queue-item"
          :class="{
            'drag-over': dragOverIndex === index,
            'dragging': dragIndex === index,
          }"
          draggable="true"
          @dragstart="handleDragStart(index)"
          @dragover="handleDragOver($event, index)"
          @dragleave="handleDragLeave"
          @drop="handleDrop(index)"
        >
          <!-- 序号 + 拖拽手柄 -->
          <div class="item-handle">
            <span class="item-index">{{ index + 1 }}</span>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" opacity="0.3">
              <circle cx="9" cy="6" r="1.5"/><circle cx="15" cy="6" r="1.5"/>
              <circle cx="9" cy="12" r="1.5"/><circle cx="15" cy="12" r="1.5"/>
              <circle cx="9" cy="18" r="1.5"/><circle cx="15" cy="18" r="1.5"/>
            </svg>
          </div>

          <!-- 内容 -->
          <div class="item-content" v-if="editingId !== msg.id">
            <div class="item-text">{{ msg.content }}</div>
            <div class="item-meta">
              <span class="item-time">{{ formatTime(msg.created_at) }}</span>
            </div>
          </div>

          <!-- 编辑模式 -->
          <div class="item-edit" v-else>
            <n-input
              v-model:value="editContent"
              type="textarea"
              :autosize="{ minRows: 1, maxRows: 4 }"
            />
            <n-space size="small" class="edit-actions">
              <n-button size="tiny" type="primary" @click="saveEdit(msg.id)">保存</n-button>
              <n-button size="tiny" @click="cancelEdit">取消</n-button>
            </n-space>
          </div>

          <!-- 操作按钮 -->
          <div class="item-actions" v-if="editingId !== msg.id">
            <button class="action-btn edit-btn" title="编辑" @click="startEdit(msg)">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
              </svg>
            </button>
            <button class="action-btn delete-btn" title="删除" @click="removeMessage(msg.id)">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="3 6 5 6 21 6"/>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 队列设置 -->
    <div class="qm-settings-section">
      <h4 class="section-label">队列设置</h4>
      <div class="settings-grid">
        <div class="setting-item">
          <div class="setting-info">
            <span class="setting-label">启用队列自动消费</span>
            <span class="setting-desc">弹窗时自动发送队列中的消息</span>
          </div>
          <n-switch v-model:value="settings.enabled" size="small" @update:value="saveSettings" />
        </div>
        <div class="setting-item">
          <div class="setting-info">
            <span class="setting-label">显示快闪弹窗</span>
            <span class="setting-desc">自动发送时显示预览弹窗</span>
          </div>
          <n-switch v-model:value="settings.show_flash_popup" size="small" @update:value="saveSettings" />
        </div>
        <div class="setting-item full-width">
          <div class="setting-info">
            <span class="setting-label">自动发送延迟: {{ settings.auto_consume_delay }}秒</span>
            <span class="setting-desc">弹窗出现后等待多久自动发送</span>
          </div>
          <n-slider
            v-model:value="settings.auto_consume_delay"
            :min="1"
            :max="10"
            :step="1"
            :tooltip="true"
            style="width: 200px;"
            @update:value="saveSettings"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.queue-manager {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100vh;
  background: #f0f2f5;
  color: #303133;
  overflow-y: auto;
}
.queue-manager.dark {
  background: #141414;
  color: #e0e0e0;
}

/* 头部 */
.qm-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  flex-shrink: 0;
}
.dark .qm-header {
  background: #1e1e1e;
  border-bottom-color: #333;
}
.qm-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.qm-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
}
.back-btn {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: 1px solid #e0e0e0;
  background: transparent;
  color: #666;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}
.back-btn:hover {
  background: #f0f0f0;
  color: #333;
}
.dark .back-btn {
  border-color: #444;
  color: #aaa;
}
.dark .back-btn:hover {
  background: #333;
  color: #ddd;
}

/* 添加区域 */
.qm-add-section {
  padding: 16px;
  background: #fff;
  margin: 8px;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.dark .qm-add-section {
  background: #1e1e1e;
}
.section-label {
  font-size: 13px;
  font-weight: 500;
  margin: 0 0 8px;
  color: #303133;
}
.dark .section-label {
  color: #e0e0e0;
}
.section-label .hint {
  font-weight: 400;
  font-size: 11px;
  color: #909399;
}
.add-input-wrap {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.add-btn {
  align-self: flex-end;
}

/* 队列列表 */
.qm-list-section {
  padding: 16px;
  background: #fff;
  margin: 0 8px 8px;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  flex: 1;
}
.dark .qm-list-section {
  background: #1e1e1e;
}
.empty-state {
  padding: 32px 0;
}
.queue-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.queue-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  background: #fafafa;
  cursor: grab;
  transition: all 0.2s;
}
.queue-item:hover {
  border-color: #c0c4cc;
}
.queue-item.dragging {
  opacity: 0.4;
}
.queue-item.drag-over {
  border-color: #1890ff;
  background: #e6f7ff;
}
.dark .queue-item {
  background: #2a2a2a;
  border-color: #444;
}
.dark .queue-item:hover {
  border-color: #555;
}
.dark .queue-item.drag-over {
  border-color: #1890ff;
  background: #1a3a5c;
}
.item-handle {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding-top: 2px;
  color: #909399;
  flex-shrink: 0;
}
.item-index {
  font-size: 12px;
  font-weight: 600;
  color: #1890ff;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #e6f7ff;
  display: flex;
  align-items: center;
  justify-content: center;
}
.dark .item-index {
  background: #1a3a5c;
}
.item-content {
  flex: 1;
  min-width: 0;
}
.item-text {
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
}
.item-meta {
  margin-top: 4px;
}
.item-time {
  font-size: 11px;
  color: #909399;
}
.item-edit {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.edit-actions {
  align-self: flex-end;
}
.item-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}
.action-btn {
  width: 26px;
  height: 26px;
  border-radius: 4px;
  border: 1px solid transparent;
  background: transparent;
  color: #909399;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}
.action-btn:hover {
  background: #f0f0f0;
}
.edit-btn:hover {
  color: #1890ff;
  border-color: #1890ff;
}
.delete-btn:hover {
  color: #ff4d4f;
  border-color: #ff4d4f;
}
.dark .action-btn:hover {
  background: #333;
}

/* 设置 */
.qm-settings-section {
  padding: 16px;
  background: #fff;
  margin: 0 8px 8px;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.dark .qm-settings-section {
  background: #1e1e1e;
}
.settings-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 10px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  background: #fafafa;
}
.setting-item.full-width {
  flex-direction: column;
  align-items: stretch;
  gap: 8px;
}
.dark .setting-item {
  background: #2a2a2a;
  border-color: #444;
}
.setting-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.setting-label {
  font-size: 13px;
  font-weight: 500;
}
.setting-desc {
  font-size: 11px;
  color: #909399;
}
</style>
