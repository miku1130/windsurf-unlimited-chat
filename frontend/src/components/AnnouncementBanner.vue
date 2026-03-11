<script setup lang="ts">
/**
 * AnnouncementBell - 公告铃铛按钮组件
 * 在header区域显示铃铛图标，点击弹出公告内容
 * 有新公告时显示小红点提示
 */
import { onMounted, ref } from 'vue'

// 公告地址通过本地 Python 服务器代理，避免跨域
const ANNOUNCEMENT_URL = '/api/announcement'

interface Props {
  currentTheme?: string
}

withDefaults(defineProps<Props>(), {
  currentTheme: 'light',
})

// 公告数据
const announcement = ref<string>('')
const hasAnnouncement = ref(false)
const showPopup = ref(false)
const dismissed = ref(false)

// 获取公告内容
async function fetchAnnouncement() {
  try {
    const res = await fetch(ANNOUNCEMENT_URL, {
      cache: 'no-cache',
    })
    if (res.ok) {
      const data = await res.json()
      if (data && data.enabled && data.content && data.content.trim()) {
        announcement.value = data.content
        hasAnnouncement.value = true
      } else {
        hasAnnouncement.value = false
      }
    }
  } catch (e) {
    console.debug('获取公告失败:', e)
    hasAnnouncement.value = false
  }
}

// 切换弹窗显示
function togglePopup() {
  // 总是尝试打开弹窗，即使当前没有公告
  showPopup.value = !showPopup.value
  if (showPopup.value) {
    dismissed.value = true
    // 若尚未获取公告，则再尝试一次
    if (!hasAnnouncement.value) {
      fetchAnnouncement()
    }
  }
}

// 关闭弹窗
function closePopup() {
  showPopup.value = false
}

onMounted(() => {
  fetchAnnouncement()
})
</script>

<template>
  <div class="announcement-bell-wrap">
    <!-- 铃铛按钮 -->
    <button
      class="bell-btn"
      :class="{ dark: currentTheme === 'dark' }"
      @click.stop="togglePopup"
      title="查看公告"
    >
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M13.73 21a2 2 0 0 1-3.46 0" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      <!-- 未读小红点（仅有公告且未读时显示） -->
      <span v-if="hasAnnouncement && !dismissed" class="bell-dot"></span>
    </button>

    <!-- 公告弹窗 -->
    <Teleport to="body">
      <div v-if="showPopup" class="announcement-overlay" @click="closePopup">
        <div
          class="announcement-popup"
          :class="{ dark: currentTheme === 'dark' }"
          @click.stop
        >
          <div class="popup-header">
            <div class="popup-title">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" style="color: #faad14;">
                <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M13.73 21a2 2 0 0 1-3.46 0" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              <span>公告</span>
            </div>
            <button class="popup-close" @click="closePopup">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
                <line x1="18" y1="6" x2="6" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                <line x1="6" y1="6" x2="18" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
              </svg>
            </button>
          </div>
          <div class="popup-body">
            <template v-if="announcement && announcement.trim()">
              {{ announcement }}
            </template>
            <template v-else>
              <em>当前没有公告。</em>
            </template>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.announcement-bell-wrap {
  position: relative;
}

/* 铃铛按钮 - 与header其他按钮风格一致 */
.bell-btn {
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
  position: relative;
}

.bell-btn:hover {
  background: #f0f0f0;
  color: #faad14;
  border-color: #faad14;
}

.bell-btn.dark {
  border-color: #444;
  color: #aaa;
}

.bell-btn.dark:hover {
  background: #444;
  color: #faad14;
  border-color: #faad14;
}

/* 未读小红点 */
.bell-dot {
  position: absolute;
  top: 2px;
  right: 2px;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #ff4d4f;
  border: 1.5px solid #fff;
}

.dark .bell-dot {
  border-color: #242424;
}

/* 遮罩层 */
.announcement-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1000;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 60px;
}

/* 弹窗卡片 */
.announcement-popup {
  width: 320px;
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.12);
  overflow: hidden;
  animation: popIn 0.2s ease;
}

.announcement-popup.dark {
  background: #2a2a2a;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.4);
}

@keyframes popIn {
  from {
    opacity: 0;
    transform: translateY(-8px) scale(0.96);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.popup-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-bottom: 1px solid #f0f0f0;
}

.dark .popup-header {
  border-bottom-color: #3a3a3a;
}

.popup-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #333;
}

.dark .popup-title {
  color: #e0e0e0;
}

.popup-close {
  width: 22px;
  height: 22px;
  border: none;
  background: none;
  color: #999;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  padding: 0;
}

.popup-close:hover {
  background: #f5f5f5;
  color: #666;
}

.dark .popup-close:hover {
  background: #3a3a3a;
  color: #ccc;
}

.popup-body {
  padding: 14px;
  font-size: 13px;
  line-height: 1.6;
  color: #555;
  word-break: break-word;
}

.dark .popup-body {
  color: #bbb;
}
</style>
