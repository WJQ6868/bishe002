<script setup lang="ts">
import { useThemeStore } from '../stores/theme'
import { Moon, Sunny } from '@element-plus/icons-vue'
import { computed } from 'vue'

const themeStore = useThemeStore()
const isDark = computed(() => themeStore.theme === 'dark')

const toggle = () => {
  themeStore.toggleTheme()
}
</script>

<template>
  <el-button 
    circle 
    :icon="isDark ? Moon : Sunny" 
    @click="toggle" 
    :title="isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode'"
  />
</template>
