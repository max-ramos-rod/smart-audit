<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import BrandLogo from '@/components/ui/BrandLogo.vue'
import { extractProblemMessage } from '@/services/api/problem'
import { resetPassword } from '@/services/auth.service'

const route = useRoute()
const router = useRouter()

const token = computed(() => String(route.query.token ?? ''))
const newPassword = ref('')
const confirmPassword = ref('')
const isLoading = ref(false)
const error = ref<string | null>(null)
const done = ref(false)

const passwordMismatch = computed(
  () => confirmPassword.value.length > 0 && newPassword.value !== confirmPassword.value,
)

async function submit() {
  if (!token.value) return
  if (newPassword.value !== confirmPassword.value) return
  isLoading.value = true
  error.value = null
  try {
    await resetPassword(token.value, newPassword.value)
    done.value = true
  } catch (err) {
    error.value = extractProblemMessage(err, 'Não foi possível redefinir a senha.')
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <div class="login-root">
    <div class="login-brand">
      <div class="lb-inner">
        <BrandLogo variant="dark-mode" :height="46" class="lb-logo" />
        <h2 class="lb-h">
          Nova senha.<br />
          Acesso restaurado.
        </h2>
        <p class="lb-p">
          Escolha uma senha segura com pelo menos 8 caracteres. O link de redefinição é de uso único.
        </p>
      </div>
      <div class="lb-pills">
        <div class="lb-pill">Mínimo 8 caracteres</div>
        <div class="lb-pill">Token de uso único</div>
        <div class="lb-pill">Acesso imediato após redefinição</div>
      </div>
    </div>

    <div class="lfa">
      <div class="lfb">
        <div class="lf-mob-logo">
          <BrandLogo variant="primary" :height="34" />
          <div class="lf-mob-name">Smart Audit</div>
        </div>

        <template v-if="!token">
          <h1 class="lf-h">Link inválido</h1>
          <p class="lf-sub">O link de redefinição está incompleto ou foi corrompido.</p>
          <button type="button" class="lf-btn" @click="router.push({ name: 'forgot-password' })">
            Solicitar novo link
          </button>
        </template>

        <template v-else-if="!done">
          <h1 class="lf-h">Redefinir senha</h1>
          <p class="lf-sub">Informe e confirme sua nova senha.</p>

          <form class="lf-form" @submit.prevent="submit">
            <label class="field">
              <span class="flabel">Nova senha</span>
              <input
                id="new-password"
                v-model="newPassword"
                type="password"
                autocomplete="new-password"
                placeholder="Mínimo 8 caracteres"
                :disabled="isLoading"
              />
            </label>

            <label class="field">
              <span class="flabel">Confirmar senha</span>
              <input
                id="confirm-password"
                v-model="confirmPassword"
                type="password"
                autocomplete="new-password"
                placeholder="Repita a senha"
                :disabled="isLoading"
                :style="passwordMismatch ? 'border-color:var(--sa-danger)' : ''"
              />
              <p
                v-if="passwordMismatch"
                style="font-size:12px;color:var(--sa-danger);margin-top:4px;"
              >
                As senhas não coincidem.
              </p>
            </label>

            <p v-if="error" class="lf-err">{{ error }}</p>

            <button
              type="submit"
              class="lf-btn"
              :disabled="isLoading || newPassword.length < 8 || passwordMismatch || !confirmPassword"
            >
              {{ isLoading ? 'Salvando...' : 'Definir nova senha' }}
            </button>
          </form>
        </template>

        <template v-else>
          <h1 class="lf-h">Senha redefinida</h1>
          <p class="lf-sub">
            Sua senha foi atualizada com sucesso. Você já pode fazer login com a nova senha.
          </p>
          <button type="button" class="lf-btn" @click="router.push({ name: 'login' })">
            Ir para o login
          </button>
        </template>

        <button
          v-if="!done"
          type="button"
          class="lf-btn"
          style="margin-top:12px;background:transparent;color:var(--sa-muted);border:1px solid var(--sa-line);"
          @click="router.push({ name: 'login' })"
        >
          Voltar para o login
        </button>
      </div>
    </div>
  </div>
</template>
