import { createApp } from 'vue'
import { Quasar, Notify, Dialog } from 'quasar'
import quasarLang from 'quasar/lang/ru'
import iconSet from 'quasar/icon-set/material-icons-outlined'
import '@quasar/extras/material-icons-outlined/material-icons-outlined.css'
import '@fontsource/inter/400.css'
import '@fontsource/inter/500.css'
import '@fontsource/inter/600.css'
import 'quasar/src/css/index.sass'
import './css/app.scss'

import App from './App.vue'
import { router } from './router'
import { initTheme } from './stores/theme'

const app = createApp(App)
app.use(Quasar, {
  plugins: { Notify, Dialog },
  lang: quasarLang,
  iconSet,
  config: {
    notify: { position: 'bottom', timeout: 2600, classes: 'sv-toast', textColor: 'white' },
  },
})
// Plain names ("search") render as Material Icons Outlined.
app.config.globalProperties.$q.iconMapFn = (name: string) =>
  /^[a-z0-9_]+$/.test(name) ? { cls: 'material-icons-outlined', content: name } : undefined
initTheme()
app.use(router).mount('#app')
