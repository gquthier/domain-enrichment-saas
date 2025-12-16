#!/usr/bin/env python3
"""
Script de test automatique pour l'enrichissement de domaines
"""
import requests
import time
import json
import pandas as pd
from pathlib import Path

API_BASE = "http://localhost:8000"

def test_upload(file_path):
    """Test l'upload d'un fichier"""
    print(f"\n📤 Test upload: {file_path}")

    with open(file_path, 'rb') as f:
        files = {'file': (file_path.name, f, 'text/csv')}
        response = requests.post(f"{API_BASE}/api/upload", files=files)

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Upload réussi!")
        print(f"   Job ID: {data['job_id']}")
        print(f"   Fichier: {data['filename']}")
        print(f"   Colonnes: {len(data['columns'])}")
        print(f"   Lignes détectées: {data['row_count']}")
        print(f"   Colonne company: {data['detected_company_col']}")
        return data
    else:
        print(f"❌ Upload échoué: {response.status_code}")
        print(f"   Erreur: {response.text}")
        return None

def test_enrich(job_id, column_mappings):
    """Test l'enrichissement"""
    print(f"\n🚀 Test enrichissement pour job: {job_id}")

    payload = {
        "job_id": job_id,
        "column_mappings": column_mappings
    }

    response = requests.post(f"{API_BASE}/api/enrich", json=payload)

    if response.status_code == 200:
        print(f"✅ Enrichissement démarré!")
        return True
    else:
        print(f"❌ Enrichissement échoué: {response.status_code}")
        print(f"   Erreur: {response.text}")
        return False

def check_status(job_id, max_wait=300):
    """Vérifie le statut d'un job"""
    print(f"\n⏳ Vérification du statut...")

    start_time = time.time()
    while time.time() - start_time < max_wait:
        response = requests.get(f"{API_BASE}/api/status/{job_id}")

        if response.status_code == 200:
            data = response.json()
            status = data['status']
            progress = data.get('progress', 0)
            total = data.get('total', 0)
            percentage = data.get('percentage', 0)
            message = data.get('message', '')

            print(f"📊 Status: {status} | Progress: {progress}/{total} ({percentage}%) | {message}")

            if status == 'completed':
                print(f"✅ Enrichissement terminé!")
                return True
            elif status == 'failed':
                print(f"❌ Enrichissement échoué!")
                print(f"   Erreur: {data.get('error')}")
                return False
        else:
            print(f"⚠️  Erreur statut: {response.status_code}")

        time.sleep(2)

    print(f"⏰ Timeout après {max_wait}s")
    return False

def download_result(job_id, output_path):
    """Télécharge le résultat"""
    print(f"\n📥 Téléchargement du résultat...")

    response = requests.get(f"{API_BASE}/api/download/{job_id}")

    if response.status_code == 200:
        with open(output_path, 'wb') as f:
            f.write(response.content)
        print(f"✅ Résultat sauvegardé: {output_path}")
        return True
    else:
        print(f"❌ Téléchargement échoué: {response.status_code}")
        return False

def create_test_file():
    """Crée un petit fichier de test"""
    test_data = {
        'companyName': [
            'Airbus',
            'Total Energies',
            'Carrefour'
        ],
        'companyIndustry': [
            'Aerospace',
            'Energy',
            'Retail'
        ],
        'linkedinDescription': [
            'Aircraft manufacturer',
            'Oil and gas company',
            'Supermarket chain'
        ]
    }

    df = pd.DataFrame(test_data)
    test_file = Path('test_companies.csv')
    df.to_csv(test_file, index=False)
    print(f"📝 Fichier de test créé: {test_file} ({len(df)} lignes)")
    return test_file

def main():
    print("=" * 60)
    print("🧪 TEST AUTOMATIQUE D'ENRICHISSEMENT DE DOMAINES")
    print("=" * 60)

    # 1. Créer fichier de test
    test_file = create_test_file()

    # 2. Upload
    upload_result = test_upload(test_file)
    if not upload_result:
        print("\n❌ ÉCHEC: Upload impossible")
        return

    job_id = upload_result['job_id']

    # 3. Préparer les mappings
    column_mappings = [
        {"source_column": "companyName", "target_column": "company name"},
        {"source_column": "companyIndustry", "target_column": "sector"},
        {"source_column": "linkedinDescription", "target_column": "description"}
    ]

    # 4. Lancer l'enrichissement
    if not test_enrich(job_id, column_mappings):
        print("\n❌ ÉCHEC: Impossible de démarrer l'enrichissement")
        return

    # 5. Surveiller le statut
    if check_status(job_id, max_wait=60):
        # 6. Télécharger le résultat
        output_file = Path(f'test_result_{job_id}.csv')
        if download_result(job_id, output_file):
            # 7. Vérifier le contenu
            result_df = pd.read_csv(output_file)
            print(f"\n📊 Résultat:")
            print(f"   Lignes: {len(result_df)}")
            print(f"   Colonnes: {list(result_df.columns)}")
            if 'URL' in result_df.columns:
                urls_found = result_df['URL'].notna().sum()
                print(f"   URLs trouvées: {urls_found}/{len(result_df)}")
                print(f"\n📋 Aperçu:")
                print(result_df[['companyName', 'URL']].head())
            print(f"\n✅ TEST RÉUSSI!")
        else:
            print(f"\n❌ ÉCHEC: Téléchargement impossible")
    else:
        print(f"\n❌ ÉCHEC: Enrichissement n'a pas terminé")

    # Cleanup
    test_file.unlink(missing_ok=True)
    print(f"\n🧹 Nettoyage terminé")

if __name__ == "__main__":
    main()
