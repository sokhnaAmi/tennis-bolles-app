/**
 * Middleware Cloudflare Pages pour rediriger les routes API vers le Worker
 */

export async function onRequest(context) {
  const url = new URL(context.request.url);
  
  // Routes qui doivent être gérées par le Worker
  const apiRoutes = ['/api/', '/public-data'];
  const shouldProxyToWorker = apiRoutes.some(route => 
    url.pathname.startsWith(route) || url.pathname === route
  );
  
  if (shouldProxyToWorker) {
    // Construire l'URL du Worker
    // Utilisez le nom de votre Worker depuis wrangler.toml
    const workerUrl = `https://tennis-bolles-app.workers.dev${url.pathname}${url.search}`;
    
    // Créer une nouvelle requête vers le Worker
    const workerRequest = new Request(workerUrl, {
      method: context.request.method,
      headers: context.request.headers,
      body: context.request.body,
    });
    
    try {
      // Faire la requête au Worker et retourner la réponse
      const response = await fetch(workerRequest);
      return response;
    } catch (error) {
      console.error('Erreur lors de la redirection vers le Worker:', error);
      return new Response(JSON.stringify({ 
        error: 'Erreur de connexion au Worker',
        message: error.message 
      }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      });
    }
  }
  
  // Pour les autres routes (fichiers statiques), continuer normalement
  return context.next();
}

