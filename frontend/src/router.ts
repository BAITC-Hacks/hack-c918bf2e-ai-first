import { createRouter, createWebHistory } from 'vue-router'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'upload', component: () => import('./pages/UploadPage.vue') },
    { path: '/analyses/:id', name: 'analysis', component: () => import('./pages/AnalysisPage.vue'), props: true },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})
