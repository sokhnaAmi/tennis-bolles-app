/**
 * Middleware Cloudflare Pages pour rediriger les routes API vers le Worker
 * 
 * Note: Pour que cela fonctionne, vous devez :
 * 1. Déployer le Worker avec: npm run deploy
 * 2. Configurer les secrets: wrangler secret put DATABASE_URL
 * 3. Vérifier que le Worker est accessible directement
 */

export async function onRequest(context) {
  const url = new URL(context.request.url);
  
  // Routes qui doivent être gérées par le Worker
  const apiRoutes = ['/api/', '/public-data'];
  const shouldProxyToWorker = apiRoutes.some(route => 
    url.pathname.startsWith(route) || url.pathname === route
  );
  
  if (shouldProxyToWorker) {
    // Option 1: Utiliser l'intégration Worker directe (si configurée dans Pages)
    // Si vous avez lié le Worker dans les paramètres Pages, utilisez:
    if (context.env && context.env.WORKER) {
      return context.env.WORKER.fetch(context.request);
    }
    
    // Option 2: Faire un fetch vers le Worker déployé
    // URL exacte de votre Worker déployé
    const workerUrl = `https://tennis-boLles-app.aminattadiop.workers.dev${url.pathname}${url.search}`;
    
    try {
      // Créer une nouvelle requête vers le Worker
      const workerRequest = new Request(workerUrl, {
        method: context.request.method,
        headers: context.request.headers,
        body: context.request.body ? await context.request.clone().body : null,
      });
      
      // Faire la requête au Worker
      const response = await fetch(workerRequest);
      
      // Retourner la réponse avec les bons headers CORS si nécessaire
      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: {
          ...Object.fromEntries(response.headers),
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, POST, PUT, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type, X-Admin-Key',
        }
      });
    } catch (error) {
      console.error('Erreur lors de la redirection vers le Worker:', error);
      return new Response(JSON.stringify({ 
        error: 'Erreur de connexion au Worker',
        message: error.message,
        hint: 'Vérifiez que le Worker est déployé et accessible à: https://tennis-boLles-app.aminattadiop.workers.dev'
      }), {
        status: 503,
        headers: { 
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*'
        }
      });
    }
  }
  
  // Pour les autres routes (fichiers statiques), continuer normalement
  return context.next();
}

