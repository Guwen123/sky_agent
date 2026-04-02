import { createRouter, createWebHistory } from 'vue-router';
import LoginPage from '../views/LoginPage.vue';
import AgentPage from '../views/AgentPage.vue';
import InfoPage from '../views/InfoPage.vue';

const routes = [
  {
    path: '/',
    redirect: '/login'
  },
  {
    path: '/login',
    name: 'Login',
    component: LoginPage
  },
  {
    path: '/agent',
    name: 'Agent',
    component: AgentPage
  },
  {
    path: '/info',
    name: 'Info',
    component: InfoPage
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

export default router;