import { createRouter, createWebHistory } from 'vue-router'

import { readAccessToken } from '@/services/api/storage'
import { useAuthStore } from '@/stores/auth/auth.store'
import { useContextStore } from '@/stores/context/context.store'
import AssetTypesView from '@/views/asset-types/AssetTypesView.vue'
import AssetsView from '@/views/assets/AssetsView.vue'
import ClientsView from '@/views/clients/ClientsView.vue'
import CompanySelectView from '@/views/auth/CompanySelectView.vue'
import ForgotPasswordView from '@/views/auth/ForgotPasswordView.vue'
import LoginView from '@/views/auth/LoginView.vue'
import ProfileView from '@/views/auth/ProfileView.vue'
import ResetPasswordView from '@/views/auth/ResetPasswordView.vue'
import HomeView from '@/views/dashboard/HomeView.vue'
import FormDetailView from '@/views/forms/FormDetailView.vue'
import FormVersionsView from '@/views/forms/FormVersionsView.vue'
import FormsView from '@/views/forms/FormsView.vue'
import SubmissionDetailView from '@/views/submissions/SubmissionDetailView.vue'
import SubmissionReportView from '@/views/submissions/SubmissionReportView.vue'
import SubmissionsView from '@/views/submissions/SubmissionsView.vue'
import AuditView from '@/views/settings/AuditView.vue'
import CompanySettingsView from '@/views/settings/CompanySettingsView.vue'
import NotificationsView from '@/views/notifications/NotificationsView.vue'
import SearchView from '@/views/search/SearchView.vue'
import TeamsView from '@/views/teams/TeamsView.vue'
import UsersView from '@/views/users/UsersView.vue'

const router = createRouter({
  history: createWebHistory('/app/'),
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
      path: '/forgot-password',
      name: 'forgot-password',
      component: ForgotPasswordView,
      meta: { guestOnly: true },
    },
    {
      path: '/reset-password',
      name: 'reset-password',
      component: ResetPasswordView,
      meta: { guestOnly: true },
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
      path: '/submissions/:id/report',
      name: 'submission-report',
      component: SubmissionReportView,
      meta: { requiresAuth: true },
    },
    {
      path: '/forms/:formId',
      name: 'form-detail',
      component: FormDetailView,
      meta: { requiresAuth: true },
    },
    {
      path: '/forms/:formId/versions',
      name: 'form-versions',
      component: FormVersionsView,
      meta: { requiresAuth: true },
    },
    {
      path: '/profile',
      name: 'profile',
      component: ProfileView,
      meta: { requiresAuth: true },
    },
    {
      path: '/company-settings',
      name: 'company-settings',
      component: CompanySettingsView,
      meta: { requiresAuth: true },
    },
    {
      path: '/audit',
      name: 'audit',
      component: AuditView,
      meta: { requiresAuth: true },
    },
    {
      path: '/notifications',
      name: 'notifications',
      component: NotificationsView,
      meta: { requiresAuth: true },
    },
    {
      path: '/search',
      name: 'search',
      component: SearchView,
      meta: { requiresAuth: true },
    },
    {
      path: '/teams',
      name: 'teams',
      component: TeamsView,
      meta: { requiresAuth: true },
    },
    {
      path: '/clients',
      name: 'clients',
      component: ClientsView,
      meta: { requiresAuth: true },
    },
    {
      path: '/asset-types',
      name: 'asset-types',
      component: AssetTypesView,
      meta: { requiresAuth: true },
    },
    {
      path: '/assets',
      name: 'assets',
      component: AssetsView,
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

    if (contextStore.context?.requires_company_selection && to.name !== 'select-company') {
      return { name: 'select-company' }
    }
  }

  return true
})

export default router
