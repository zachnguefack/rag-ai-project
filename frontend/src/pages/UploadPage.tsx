import { FormEvent, useState } from 'react';
import { JsonPanel } from '../components/JsonPanel';
import { PageHeader } from '../components/PageHeader';
import { adminApi } from '../lib/api/admin';

export function UploadPage() {
  const [departmentId, setDepartmentId] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [filePath, setFilePath] = useState('');
  const [folderPath, setFolderPath] = useState('');
  const [result, setResult] = useState<unknown>(null);

  const upload = async (e: FormEvent) => { e.preventDefault(); if (!file) return; setResult(await adminApi.uploadDepartmentFile(departmentId, file)); };
  const ingestFile = async (e: FormEvent) => { e.preventDefault(); setResult(await adminApi.ingestFilePath(departmentId, filePath)); };
  const ingestFolder = async (e: FormEvent) => { e.preventDefault(); setResult(await adminApi.ingestFolderPath(departmentId, folderPath)); };

  return (
    <>
      <PageHeader title="Department Ingestion" subtitle="Upload files or ingest by server file path/folder path" />
      <section className="grid two-col">
        <form className="card" onSubmit={upload}><h3>Upload</h3><input placeholder="department_id" value={departmentId} onChange={(e) => setDepartmentId(e.target.value)} required /><input type="file" onChange={(e) => setFile(e.target.files?.[0] || null)} required /><button>Upload</button></form>
        <form className="card" onSubmit={ingestFile}><h3>Ingest File Path</h3><input placeholder="department_id" value={departmentId} onChange={(e) => setDepartmentId(e.target.value)} required /><input placeholder="/data/imports/file.pdf" value={filePath} onChange={(e) => setFilePath(e.target.value)} required /><button>Ingest</button></form>
        <form className="card" onSubmit={ingestFolder}><h3>Ingest Folder Path</h3><input placeholder="department_id" value={departmentId} onChange={(e) => setDepartmentId(e.target.value)} required /><input placeholder="/data/imports/folder" value={folderPath} onChange={(e) => setFolderPath(e.target.value)} required /><button>Ingest Folder</button></form>
      </section>
      <JsonPanel data={result} />
    </>
  );
}
