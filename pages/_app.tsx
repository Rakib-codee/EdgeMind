import type { AppProps } from 'next/app'
import Head from 'next/head'
import Layout from '../src/components/Layout'
import { AppStateProvider } from '../src/lib/state'
import '../src/styles/globals.css'

export default function App({ Component, pageProps }: AppProps) {
  return (
    <AppStateProvider>
      <Head>
        <title>EdgeMind — Edge–Cloud Orchestrator</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
      </Head>
      <Layout>
        <Component {...pageProps} />
      </Layout>
    </AppStateProvider>
  )
}
