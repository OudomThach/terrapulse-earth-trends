import '@fontsource-variable/inter'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import { MetaProvider } from './meta'
import { AppStateProvider } from './state'
import './styles.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AppStateProvider>
      <MetaProvider>
        <App />
      </MetaProvider>
    </AppStateProvider>
  </StrictMode>,
)
