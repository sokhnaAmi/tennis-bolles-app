/**
 * Routes API pour l'administration
 */

import { checkAuth, unauthorizedResponse } from '../auth.js';
import { getSQL, loadAdminSecret, saveAdminSecret } from '../db.js';

/**
 * GET /api/ping - Vérification de l'authentification
 */
export async function handlePing(request, env) {
  const adminSecret = await loadAdminSecret(env.DATABASE_URL, env.ADMIN_SECRET);
  
  if (!checkAuth(request, adminSecret)) {
    return unauthorizedResponse();
  }
  
  return new Response('', { status: 204 });
}

/**
 * GET /api/data - Récupère toutes les données (admin)
 */
export async function handleGetData(request, env) {
  const { getSQL } = await import('../db.js');
  const adminSecret = await loadAdminSecret(env.DATABASE_URL, env.ADMIN_SECRET);
  
  if (!checkAuth(request, adminSecret)) {
    return unauthorizedResponse();
  }
  
  try {
    const sql = await getSQL(env.DATABASE_URL);
    
    // Récupérer les catégories
    const categories = await sql`
      SELECT id, categorie, question, reponse FROM categories ORDER BY id;
    `;
    
    // Récupérer les bris
    const bris = await sql`
      SELECT id, affirmation, reponse FROM bris ORDER BY id;
    `;
    
    const payload = {
      categories: categories.map(row => ({
        id: row.id,
        categorie: row.categorie,
        question: row.question,
        reponse: row.reponse
      })),
      bris: bris.map(row => ({
        id: row.id,
        affirmation: row.affirmation,
        reponse: row.reponse
      }))
    };
    
    return new Response(JSON.stringify(payload), {
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error) {
    console.error('Erreur /api/data:', error);
    return new Response(JSON.stringify({ error: 'Erreur de base de données' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * GET /public-data - Récupère les données publiques (sans auth)
 */
export async function handlePublicData(request, env) {
  try {
    const { getSQL } = await import('../db.js');
    const sql = await getSQL(env.DATABASE_URL);
    
    // Récupérer les catégories
    const categories = await sql`
      SELECT id, categorie, question, reponse FROM categories ORDER BY id;
    `;
    
    // Récupérer les bris
    const bris = await sql`
      SELECT id, affirmation, reponse FROM bris ORDER BY id;
    `;
    
    const payload = {
      categories: categories.map(row => ({
        id: row.id,
        categorie: row.categorie,
        question: row.question,
        reponse: row.reponse
      })),
      bris: bris.map(row => ({
        id: row.id,
        affirmation: row.affirmation,
        reponse: row.reponse
      }))
    };
    
    return new Response(JSON.stringify(payload), {
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error) {
    console.error('Erreur /public-data:', error);
    return new Response(JSON.stringify({ erreur: 'erreur de base de données' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * PUT /api/data - Enregistre toutes les données (admin)
 */
export async function handlePutData(request, env) {
  const { getSQL } = await import('../db.js');
  const adminSecret = await loadAdminSecret(env.DATABASE_URL, env.ADMIN_SECRET);
  
  if (!checkAuth(request, adminSecret)) {
    return unauthorizedResponse();
  }
  
  try {
    const payload = await request.json();
    const cats = payload.categories || [];
    const bris = payload.bris || [];
    
    const sql = await getSQL(env.DATABASE_URL);
    
    // Supprimer toutes les données existantes
    await sql`DELETE FROM categories;`;
    await sql`DELETE FROM bris;`;
    
    // Insérer les catégories en batch (une par une pour compatibilité)
    if (cats.length > 0) {
      for (const c of cats) {
        await sql`
          INSERT INTO categories (id, categorie, question, reponse)
          VALUES (${c.id}, ${c.categorie}, ${c.question}, ${c.reponse});
        `;
      }
    }
    
    // Insérer les bris en batch (une par une pour compatibilité)
    if (bris.length > 0) {
      for (const b of bris) {
        await sql`
          INSERT INTO bris (id, affirmation, reponse)
          VALUES (${b.id}, ${b.affirmation}, ${b.reponse});
        `;
      }
    }
    
    return new Response(JSON.stringify({ ok: true }), {
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error) {
    console.error('Erreur /api/data PUT:', error);
    console.error('Stack:', error.stack);
    return new Response(JSON.stringify({ 
      error: 'Erreur lors de l\'enregistrement',
      message: error.message,
      details: process.env.NODE_ENV === 'development' ? error.stack : undefined
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * POST /api/change-password - Change le mot de passe admin
 */
export async function handleChangePassword(request, env) {
  const adminSecret = await loadAdminSecret(env.DATABASE_URL, env.ADMIN_SECRET);
  
  if (!checkAuth(request, adminSecret)) {
    return unauthorizedResponse();
  }
  
  try {
    const data = await request.json();
    const newPassword = (data.new_password || '').trim();
    
    if (!newPassword) {
      return new Response(JSON.stringify({ error: 'missing new_password' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    await saveAdminSecret(env.DATABASE_URL, newPassword);
    
    return new Response(JSON.stringify({ ok: true }), {
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error) {
    console.error('Erreur /api/change-password:', error);
    return new Response(JSON.stringify({ error: 'Erreur lors du changement de mot de passe' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

