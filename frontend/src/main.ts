import { createApp } from 'vue'
import { Quasar, Notify, Dialog } from 'quasar'
import quasarLang from 'quasar/lang/ru'
import '@quasar/extras/material-icons/material-icons.css'
import '@quasar/extras/roboto-font/roboto-font.css'
import 'quasar/src/css/index.sass'
import './css/app.scss'

import App from './App.vue'
import { router } from './router'

createApp(App)
  .use(Quasar, {
    plugins: { Notify, Dialog },
    lang: quasarLang,
    config: { notify: { position: 'top-right', timeout: 5000 } },
  })
  .use(router)
  .mount('#app')
