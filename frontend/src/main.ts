import { createApp } from 'vue'
import {
  create,
  NButton,
  NCard,
  NCheckbox,
  NConfigProvider,
  NDialogProvider,
  NImage,
  NImageGroup,
  NInput,
  NMessageProvider,
  NModal,
  NNotificationProvider,
  NSpace,
  NSwitch,
  NTooltip,
} from 'naive-ui'
import App from './App.vue'
import './styles/main.css'

const naive = create({
  components: [
    NButton,
    NCard,
    NCheckbox,
    NConfigProvider,
    NDialogProvider,
    NImage,
    NImageGroup,
    NInput,
    NMessageProvider,
    NModal,
    NNotificationProvider,
    NSpace,
    NSwitch,
    NTooltip,
  ],
})

const app = createApp(App)
app.use(naive)
app.mount('#app')
