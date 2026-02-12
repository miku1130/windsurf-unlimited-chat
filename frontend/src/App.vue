<script setup lang="ts">
// App.vue - 根组件，包裹McpPopup + SettingsPage + QueueManager + QueueFlashPopup
import type { McpRequest, McpResponse, QueueMessage } from './types/popup'
import { darkTheme } from 'naive-ui'
import { computed, onMounted, ref } from 'vue'

import McpPopup from './components/McpPopup.vue'
import QueueFlashPopup from './components/QueueFlashPopup.vue'
import QueueManager from './components/QueueManager.vue'
import SettingsPage from './components/SettingsPage.vue'

const currentTheme = ref<string>('light')
const request = ref<McpRequest | null>(null)
const currentPage = ref<'popup' | 'settings' | 'queue_manager' | 'queue_flash'>('popup')

// 队列消费模式相关
const appMode = ref<string>('feedback')  // feedback | queue_consume | queue_manager
const queueMessage = ref<QueueMessage | null>(null)
const queueCount = ref(0)
const autoConsumeDelay = ref(3)

// Naive UI 主题
const naiveTheme = computed(() => currentTheme.value === 'dark' ? darkTheme : null)

// 从后端获取初始数据
async function fetchConfig() {
  try {
    const res = await fetch('/api/config')
    if (res.ok) {
      const config = await res.json()
      request.value = {
        id: config.request_id || `req_${Date.now()}`,
        message: config.summary || config.message || '',
        predefined_options: config.predefined_options || [],
        is_markdown: config.is_markdown ?? true,
      }
      if (config.theme) {
        currentTheme.value = config.theme
      }

      // 检测模式
      appMode.value = config.mode || 'feedback'

      if (appMode.value === 'queue_consume') {
        // 队列自动消费模式 → 显示快闪弹窗
        queueMessage.value = config.queue_message || null
        queueCount.value = config.queue_count || 0
        autoConsumeDelay.value = config.auto_consume_delay || 3
        currentPage.value = 'queue_flash'
      } else if (appMode.value === 'queue_manager') {
        // 队列管理器模式
        currentPage.value = 'queue_manager'
      } else {
        currentPage.value = 'popup'
      }
    }
  }
  catch (error) {
    console.error('获取配置失败:', error)
    request.value = {
      id: `req_${Date.now()}`,
      message: '等待AI消息...',
      predefined_options: [],
      is_markdown: true,
    }
  }
}

function handleResponse(_response: McpResponse) {
  console.log('提交成功，窗口即将关闭')
  setTimeout(() => {
    window.close()
  }, 500)
}

function handleCancel() {
  window.close()
}

function handleThemeChange(theme: string) {
  currentTheme.value = theme
  document.documentElement.classList.toggle('dark', theme === 'dark')
}

function handleQueueFlashCancel() {
  // 用户取消了队列自动发送，切换到正常弹窗
  currentPage.value = 'popup'
}

function handleQueueFlashSubmitted() {
  console.log('队列消息已自动发送，窗口即将关闭')
  setTimeout(() => {
    window.close()
  }, 500)
}

onMounted(() => {
  fetchConfig()
})
</script>

<template>
  <n-config-provider :theme="naiveTheme">
    <n-message-provider>
      <n-notification-provider>
        <n-dialog-provider>
          <div class="app-container" :class="{ dark: currentTheme === 'dark' }">
            <!-- 正常弹窗模式 -->
            <McpPopup
              v-if="currentPage === 'popup'"
              :request="request"
              :current-theme="currentTheme"
              @response="handleResponse"
              @cancel="handleCancel"
              @theme-change="handleThemeChange"
            >
              <template #header-extra>
                <button
                  class="settings-gear-btn"
                  :class="{ dark: currentTheme === 'dark' }"
                  @click="currentPage = 'queue_manager'"
                  title="队列管理"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/>
                    <line x1="8" y1="18" x2="21" y2="18"/>
                    <line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/>
                    <line x1="3" y1="18" x2="3.01" y2="18"/>
                  </svg>
                </button>
                <button
                  class="settings-gear-btn"
                  :class="{ dark: currentTheme === 'dark' }"
                  @click="currentPage = 'settings'"
                  title="设置"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <path d="M12 15a3 3 0 100-6 3 3 0 000 6z" stroke="currentColor" stroke-width="2"/>
                    <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" stroke="currentColor" stroke-width="2"/>
                  </svg>
                </button>
              </template>
            </McpPopup>

            <!-- 队列快闪弹窗 -->
            <QueueFlashPopup
              v-else-if="currentPage === 'queue_flash'"
              :message="queueMessage"
              :queue-count="queueCount"
              :delay="autoConsumeDelay"
              :current-theme="currentTheme"
              @cancel="handleQueueFlashCancel"
              @submitted="handleQueueFlashSubmitted"
            />

            <!-- 队列管理页面 -->
            <QueueManager
              v-else-if="currentPage === 'queue_manager'"
              :current-theme="currentTheme"
              @back="currentPage = appMode === 'queue_manager' ? 'queue_manager' : 'popup'"
              @theme-change="handleThemeChange"
            />

            <!-- 设置页面 -->
            <SettingsPage
              v-else
              :current-theme="currentTheme"
              @back="currentPage = 'popup'"
              @theme-change="handleThemeChange"
            />
          </div>
        </n-dialog-provider>
      </n-notification-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<style scoped>
.app-container {
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  margin: 0;
  padding: 0;
  position: relative;
}

.settings-gear-btn {
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
  transition: all 0.2s ease;
  padding: 0;
  margin-right: 4px;
}

.settings-gear-btn:hover {
  background: #f0f0f0;
  color: #333;
  border-color: #ccc;
}

.settings-gear-btn.dark {
  border-color: #444;
  color: #aaa;
}

.settings-gear-btn.dark:hover {
  background: #444;
  color: #ddd;
  border-color: #555;
}
</style>
