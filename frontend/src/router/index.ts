import { createRouter, createWebHistory } from 'vue-router'

import { readAccessToken } from '@/services/api/storage'
import { useAuthStore } from '@/stores/auth/auth.store'
import { useContextStore } from '@/stores/context/context.store'
import CompanySelectView from '@/views/auth/CompanySelectView.vue'
import LoginView from '@/views/auth/LoginView.vue'
import HomeView from '@/views/dashboard/HomeView.vue'
import FormVersionsView from '@/views/forms/FormVersionsView.vue'
import FormsView from '@/views/forms/FormsView.vue'
import SubmissionDetailView from '@/views/submissions/SubmissionDetailView.vue'
import SubmissionsView from '@/views/submissions/SubmissionsView.vue'
import TeamsView from '@/views/teams/TeamsView.vue'
import UsersView from '@/views/users/UsersView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: { guestOnly: true },
    },
    {
      path: '/select-company',
      name: 'select-company',
      component: CompanySelectView,
      meta: { requiresAuth: true },
    },
    {
      path: '/',
      name: 'home',
      component: HomeView,
      meta: { requiresAuth: true },
    },
    {
      path: '/users',
      name: 'users',
      component: UsersView,
      meta: { requiresAuth: true },
    },
    {
      path: '/forms',
      name: 'forms',
      component: FormsView,
      meta: { requiresAuth: true },
    },
    {
      path: '/submissions',
      name: 'submissions',
      component: SubmissionsView,
      meta: { requiresAuth: true },
    },
    {
      path: '/submissions/:id',
      name: 'submission-detail',
      component: SubmissionDetailView,
      meta: { requiresAuth: true },
    },
    {
      path: '/forms/:formId/versions',
      name: 'form-versions',
      component: FormVersionsView,
      meta: { requiresAuth: true },
    },
    {
      path: '/teams',
      name: 'teams',
      component: TeamsView,
      meta: { requiresAuth: true },
    },
  ],
})

router.beforeEach(async (to) => {
  const token = readAccessToken()
  const requiresAuth = Boolean(to.meta.requiresAuth)
  const guestOnly = Boolean(to.meta.guestOnly)

  if (requiresAuth && !token) {
    return { name: 'login' }
  }

  if (guestOnly && token) {
    return { name: 'home' }
  }

  if (requiresAuth && token) {
    const contextStore = useContextStore()
    const authStore = useAuthStore()
    if (!contextStore.context && !contextStore.isLoading) {
      try {
        await contextStore.bootstrap()
      } catch {
        return { name: 'login' }
      }
    }
    if (contextStore.context?.user && !authStore.user) {
      authStore.setUser(contextStore.context.user)
    }

    if (
      contextStore.context?.requires_company_selection &&
      to.name !== 'select-company'
    ) {
      return { name: 'select-company' }
    }
  }

  return true
})

export default router
