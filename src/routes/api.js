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
 * Version sécurisée et optimisée :
 * - INSERT/UPDATE d'abord (en batch) pour éviter la perte de données
 * - DELETE ensuite seulement si l'insertion réussit
 * - Batch pour éviter "Too many subrequests"
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
    
    // Récupérer les IDs existants pour savoir quoi supprimer APRÈS l'insertion
    const existingCats = await sql`SELECT id FROM categories;`;
    const existingBris = await sql`SELECT id FROM bris;`;
    const existingCatIds = new Set(existingCats.map(r => r.id));
    const existingBrisIds = new Set(existingBris.map(r => r.id));
    
    const newCatIds = new Set(cats.map(c => c.id));
    const newBrisIds = new Set(bris.map(b => b.id));
    
    // Identifier ce qui doit être supprimé (mais on le fera APRÈS l'insertion)
    const catsToDelete = [...existingCatIds].filter(id => !newCatIds.has(id));
    const brisToDelete = [...existingBrisIds].filter(id => !newBrisIds.has(id));
    
    // D'ABORD : Insérer ou mettre à jour en batch (UPSERT)
    // Si cela échoue, les données existantes ne sont PAS supprimées
    
    // Catégories : batch insert avec UNNEST et arrays PostgreSQL
    // Cela permet d'insérer plusieurs lignes en une seule requête SQL
    // Évite complètement "Too many subrequests"
    if (cats.length > 0) {
      const batchSize = 500; // Grands batches car une seule requête par batch
      
      for (let i = 0; i < cats.length; i += batchSize) {
        const batch = cats.slice(i, i + batchSize);
        
        // Extraire les valeurs en arrays
        const ids = batch.map(c => c.id);
        const categories = batch.map(c => c.categorie);
        const questions = batch.map(c => c.question);
        const reponses = batch.map(c => c.reponse);
        
        // Utiliser UNNEST pour insérer plusieurs lignes en une seule requête
        await sql`
          INSERT INTO categories (id, categorie, question, reponse)
          SELECT * FROM UNNEST(
            ${ids}::int[],
            ${categories}::text[],
            ${questions}::text[],
            ${reponses}::text[]
          )
          ON CONFLICT (id) DO UPDATE
          SET categorie = EXCLUDED.categorie,
              question = EXCLUDED.question,
              reponse = EXCLUDED.reponse;
        `;
      }
    }
    
    // Bris : batch insert avec UNNEST
    if (bris.length > 0) {
      const batchSize = 500;
      
      for (let i = 0; i < bris.length; i += batchSize) {
        const batch = bris.slice(i, i + batchSize);
        
        const ids = batch.map(b => b.id);
        const affirmations = batch.map(b => b.affirmation);
        const reponses = batch.map(b => b.reponse);
        
        await sql`
          INSERT INTO bris (id, affirmation, reponse)
          SELECT * FROM UNNEST(
            ${ids}::int[],
            ${affirmations}::text[],
            ${reponses}::text[]
          )
          ON CONFLICT (id) DO UPDATE
          SET affirmation = EXCLUDED.affirmation,
              reponse = EXCLUDED.reponse;
        `;
      }
    }
    
    // ENSUITE : Supprimer seulement ce qui n'est plus nécessaire
    // On le fait après l'insertion pour plus de sécurité
    if (catsToDelete.length > 0) {
      const deleteBatchSize = 100;
      for (let i = 0; i < catsToDelete.length; i += deleteBatchSize) {
        const batch = catsToDelete.slice(i, i + deleteBatchSize);
        await sql`DELETE FROM categories WHERE id = ANY(${batch});`;
      }
    }
    
    if (brisToDelete.length > 0) {
      const deleteBatchSize = 100;
      for (let i = 0; i < brisToDelete.length; i += deleteBatchSize) {
        const batch = brisToDelete.slice(i, i + deleteBatchSize);
        await sql`DELETE FROM bris WHERE id = ANY(${batch});`;
      }
    }
    
    return new Response(JSON.stringify({ ok: true }), {
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error) {
    console.error('Erreur /api/data PUT:', error);
    console.error('Message:', error.message);
    console.error('Stack:', error.stack);
    // En cas d'erreur, les données existantes ne sont PAS supprimées
    // car on fait INSERT/UPDATE avant DELETE
    return new Response(JSON.stringify({ 
      error: 'Erreur lors de l\'enregistrement',
      message: error.message
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

