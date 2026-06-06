<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { requestPasswordReset } from '@/services/auth.service'
import { extractProblemMessage } from '@/services/api/problem'

const router = useRouter()
const email = ref('')
const isLoading = ref(false)
const error = ref<string | null>(null)
const sent = ref(false)

async function submit() {
  if (!email.value.trim()) return
  isLoading.value = true
  error.value = null
  try {
    await requestPasswordReset(email.value.trim())
    sent.value = true
  } catch (err: any) {
    error.value = extractProblemMessage(err, 'Não foi possível enviar o link. Tente novamente.')
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <div class="login-root">
    <div class="login-brand">
      <div class="lb-inner">
        <div class="lb-mark">SA</div>
        <h2 class="lb-h">
          Recuperação de acesso.<br />
          Segura e direta.
        </h2>
        <p class="lb-p">
          Informe o e-mail da sua conta. Se ele estiver cadastrado, você receberá um link de redefinição válido por 1 hora.
        </p>
      </div>
      <div class="lb-pills">
        <div class="lb-pill">Link expira em 1 hora</div>
        <div class="lb-pill">Token de uso único</div>
        <div class="lb-pill">Sem revelar dados cadastrais</div>
      </div>
    </div>

    <div class="lfa">
      <div class="lfb">
        <div class="lf-mob-logo">
          <div class="lf-mob-mark">SA</div>
          <div class="lf-mob-name">Smart Audit</div>
        </div>

        <template v-if="!sent">
          <h1 class="lf-h">Recuperação de senha</h1>
          <p class="lf-sub">
            Informe seu e-mail para receber o link de redefinição.
          </p>

          <form class="lf-form" @submit.prevent="submit">
            <label class="field">
              <span class="flabel">E-mail</span>
              <input
                id="email"
                v-model="email"
                type="email"
                autocomplete="email"
                placeholder="seu@email.com"
                :disabled="isLoading"
              />
            </label>

            <p v-if="error" class="lf-err">{{ error }}</p>

            <button
              type="submit"
              class="lf-btn"
              :disabled="isLoading || !email.trim()"
            >
              {{ isLoading ? 'Enviando...' : 'Enviar link de recuperação' }}
            </button>
          </form>
        </template>

        <template v-else>
          <h1 class="lf-h">Link enviado</h1>
          <p class="lf-sub">
            Se o e-mail <strong>{{ email }}</strong> estiver cadastrado, você receberá um link de redefinição em instantes. Verifique também a pasta de spam.
          </p>
          <div class="info-box" style="margin-bottom:20px;">
            O link é válido por 1 hora e pode ser usado uma única vez.
          </div>
        </template>

        <button
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
