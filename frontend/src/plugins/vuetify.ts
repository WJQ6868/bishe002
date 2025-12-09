import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { aliases, mdi } from 'vuetify/iconsets/mdi'
import '@mdi/font/css/materialdesignicons.css'

export const vuetify = createVuetify({
  components,
  directives,
  icons: {
    defaultSet: 'mdi',
    aliases,
    sets: {
      mdi,
    },
  },
  theme: {
    defaultTheme: 'light',
    themes: {
      light: {
        colors: {
          primary: '#2196F3', // Student Blue
          secondary: '#4CAF50', // Teacher Green
          tertiary: '#9C27B0', // Admin Purple
          accent: '#FF9800',
          error: '#F44336',
          success: '#388E3C',
          background: '#FAFAFA',
          surface: '#FFFFFF',
        },
      },
    },
  },
})
