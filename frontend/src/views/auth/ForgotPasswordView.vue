<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<template>
  <div class="login-root">
    <div class="login-brand">
      <div class="lb-inner">
        <div class="lb-mark">SA</div>
        <h2 class="lb-h">
          Recuperação de acesso.<br />
          Fluxo seguro.<br />
          Em evolução.
        </h2>
        <p class="lb-p">
          Esta etapa ainda não foi integrada ao backend de identidade. Por enquanto, o acesso deve ser recuperado com o administrador da empresa.
        </p>
      </div>
      <div class="lb-pills">
        <div class="lb-pill">Fluxo de recuperação planejado</div>
        <div class="lb-pill">Validação por e-mail corporativo</div>
        <div class="lb-pill">Experiencia alinhada ao app principal</div>
      </div>
    </div>

    <div class="lfa">
      <div class="lfb">
        <div class="lf-mob-logo">
          <div class="lf-mob-mark">SA</div>
          <div class="lf-mob-name">Smart Audit</div>
        </div>

        <h1 class="lf-h">Recuperação de senha</h1>
        <p class="lf-sub">
          Este fluxo ainda não está disponível. Se precisar acessar a plataforma agora, fale com o administrador da sua empresa.
        </p>

        <div class="info-box" style="margin-bottom: 16px;">
          O módulo de recuperação de senha será conectado ao backend de identidade em uma próxima etapa.
        </div>

        <button type="button" class="lf-btn" @click="router.push({ name: 'login' })">
          Voltar para o login
        </button>
      </div>
    </div>
  </div>
</template>
