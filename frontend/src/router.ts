import { createRouter, createWebHistory } from 'vue-router'

export const router = createRouter({
  history: createWebHistory(),
  scrollBehavior: (to, from) => (to.path === from.path ? false : { top: 0 }),
  routes: [
    { path: '/', redirect: '/new' },
    { path: '/new', name: 'new', component: () => import('./pages/NewAnalysisPage.vue'), meta: { crumb: 'Новый анализ' } },
    {
      path: '/analysis/:id',
      component: () => import('./pages/AnalysisShell.vue'),
      props: true,
      children: [
        { path: 'run', name: 'run', component: () => import('./pages/RunPage.vue') },
        { path: '', name: 'overview', component: () => import('./pages/OverviewPage.vue') },
        { path: 'conclusion', name: 'conclusion', component: () => import('./pages/ConclusionPage.vue') },
      ],
    },
    // Links from the first prototype.
    { path: '/analyses/:id', redirect: (to) => `/analysis/${String(to.params.id)}` },
    { path: '/:pathMatch(.*)*', redirect: '/new' },
  ],
})
