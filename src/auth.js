/**
 * Fonctions d'authentification
 */

/**
 * Vérifie que le header X-Admin-Key correspond au mot de passe admin
 * @param {Request} request - Requête HTTP
 * @param {string} adminSecret - Mot de passe admin actuel
 * @returns {boolean} - True si authentifié
 */
export function checkAuth(request, adminSecret) {
  const adminKey = request.headers.get('X-Admin-Key') || '';
  return adminKey === adminSecret;
}

/**
 * Retourne une réponse 401 (Non autorisé)
 * @returns {Response}
 */
export function unauthorizedResponse() {
  return new Response('', { status: 401 });
}

