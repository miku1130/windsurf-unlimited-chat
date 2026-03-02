<script setup lang="ts">
/**
 * AnnouncementBanner - 公告横幅组件
 * 从远程服务器获取公告内容并展示在首页顶部
 */
import { onMounted, ref } from 'vue'

// 公告远程地址（使用PHP API，自带CORS头）
const ANNOUNCEMENT_URL = 'https://8.134.87.73/announcement_api.php'

interface Props {
  currentTheme?: string
}

withDefaults(defineProps<Props>(), {
  currentTheme: 'light',
})

// 公告数据
const announcement = ref<string>('')
const visible = ref(false)
const dismissed = ref(false)
const loading = ref(true)

// 获取公告内容
async function fetchAnnouncement() {
  loading.value = true
  try {
    const res = await fetch(ANNOUNCEMENT_URL, {
      cache: 'no-cache',
    })
    if (res.ok) {
      const data = await res.json()
      // 支持 { content: "公告内容", enabled: true }
      if (data && data.enabled && data.content && data.content.trim()) {
        announcement.value = data.content
        visible.value = true
      } else {
        visible.value = false
      }
    }
  } catch (e) {
    // 获取失败时静默处理，不显示公告
    console.debug('获取公告失败:', e)
    visible.value = false
  } finally {
    loading.value = false
  }
}

// 关闭公告
function dismiss() {
  dismissed.value = true
}

onMounted(() => {
  fetchAnnouncement()
})
</script>

<template>
  <div
    v-if="visible && !dismissed"
    class="announcement-banner"
    :class="{ dark: currentTheme === 'dark' }"
  >
    <div class="announcement-icon">
      <!-- 喇叭图标 -->
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M13.73 21a2 2 0 0 1-3.46 0" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </div>
    <div class="announcement-text">{{ announcement }}</div>
    <button class="announcement-close" @click="dismiss" title="关闭公告">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
        <line x1="18" y1="6" x2="6" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        <line x1="6" y1="6" x2="18" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      </svg>
    </button>
  </div>
</template>

<style scoped>
.announcement-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  margin: 8px 8px 0 8px;
  background: #fffbe6;
  border: 1px solid #ffe58f;
  border-radius: 6px;
  font-size: 12px;
  color: #8c6e00;
  line-height: 1.5;
}

.announcement-banner.dark {
  background: #2b2611;
  border-color: #594e1a;
  color: #d4b106;
}

.announcement-icon {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  color: #faad14;
}

.announcement-text {
  flex: 1;
  word-break: break-word;
}

.announcement-close {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  border: none;
  background: none;
  color: inherit;
  opacity: 0.5;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 3px;
  padding: 0;
}

.announcement-close:hover {
  opacity: 1;
  background: rgba(0, 0, 0, 0.06);
}

.dark .announcement-close:hover {
  background: rgba(255, 255, 255, 0.1);
}
</style>
