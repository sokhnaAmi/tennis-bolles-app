/**
 * Cloudflare Worker principal - Router pour toutes les routes
 */

import * as apiRoutes from './routes/api.js';

/**
 * Gère toutes les requêtes entrantes
 */
export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;
    const method = request.method;

    // Routes API
    if (path === '/api/ping' && method === 'GET') {
      return await apiRoutes.handlePing(request, env);
    }
    
    if (path === '/api/data' && method === 'GET') {
      return await apiRoutes.handleGetData(request, env);
    }
    
    if (path === '/api/data' && method === 'PUT') {
      return await apiRoutes.handlePutData(request, env);
    }
    
    if (path === '/api/change-password' && method === 'POST') {
      return await apiRoutes.handleChangePassword(request, env);
    }
    
    if (path === '/public-data' && method === 'GET') {
      return await apiRoutes.handlePublicData(request, env);
    }

    // Routes statiques - Pages HTML
    // En développement, Wrangler sert automatiquement les fichiers statiques
    // On laisse Wrangler gérer ces routes via l'API Assets
    if (path === '/' || path === '/index.html') {
      return await serveStaticFile('index.html', env, request);
    }
    
    if (path === '/admin' || path === '/admin.html') {
      return await serveStaticFile('admin.html', env, request);
    }

    // Si aucun match, retourner 404
    return new Response('Not Found', { status: 404 });
  }
};

/**
 * Sert un fichier statique
 * En développement local, on utilise l'API Assets de Wrangler
 * En production, Cloudflare Pages servira ces fichiers
 */
async function serveStaticFile(filename, env, request) {
  try {
    // Utiliser l'API Assets de Wrangler si disponible
    if (env.ASSETS) {
      const url = new URL(request.url);
      url.pathname = `/${filename}`;
      return await env.ASSETS.fetch(url);
    }
    
    // Sinon, essayer de charger via fetch (pour le développement local)
    const url = new URL(request.url);
    url.pathname = `/${filename}`;
    const response = await fetch(url.toString());
    
    if (response.ok) {
      return response;
    }
    
    // Si tout échoue, retourner une erreur
    return new Response(`Fichier ${filename} non trouvé. En développement, assurez-vous que les fichiers HTML sont dans le dossier racine.`, {
      status: 404,
      headers: { 'Content-Type': 'text/plain; charset=utf-8' }
    });
  } catch (error) {
    console.error('Erreur serveStaticFile:', error);
    return new Response('Error serving file', { status: 500 });
  }
}

