import { useState, useEffect } from 'react'
import './App.css'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080'

function App() {
  const [files, setFiles] = useState([])
  const [directories, setDirectories] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [prefix, setPrefix] = useState('')
  const [nextToken, setNextToken] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadPath, setUploadPath] = useState('')

  const fetchFiles = async (token = null, prefixOverride = null) => {
    setLoading(true)
    setError(null)

    try {
      const params = new URLSearchParams({
        prefix: prefixOverride !== null ? prefixOverride : prefix,
        max_keys: '100',
      })

      if (token) {
        params.append('continuation_token', token)
      }

      const response = await fetch(`${API_BASE_URL}/files?${params}`)

      if (!response.ok) {
        throw new Error(`HTTP error: ${response.status}`)
      }

      const data = await response.json()

      if (token) {
        setFiles(prev => [...prev, ...data.files])
      } else {
        setFiles(data.files)
        setDirectories(data.directories || [])
      }

      setNextToken(data.next_token)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchFiles()
  }, [])

  const handleSearch = (e) => {
    e.preventDefault()
    fetchFiles()
  }

  const handleNavigate = (newPrefix) => {
    setPrefix(newPrefix)
    setNextToken(null)
    fetchFiles(null, newPrefix)
  }

  const handleGoUp = () => {
    const parts = prefix.split('/').filter(Boolean)
    parts.pop()
    const newPrefix = parts.length > 0 ? parts.join('/') + '/' : ''
    handleNavigate(newPrefix)
  }

  const handleDelete = async (key) => {
    if (!confirm(`Delete ${key}?`)) {
      return
    }

    try {
      const response = await fetch(`${API_BASE_URL}/files/${encodeURIComponent(key)}`, {
        method: 'DELETE',
      })

      if (!response.ok) {
        throw new Error(`Failed to delete: ${response.status}`)
      }

      setFiles(files.filter(f => f.key !== key))
    } catch (err) {
      setError(err.message)
    }
  }

  const handleUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return

    setUploading(true)
    setUploadProgress(0)
    setError(null)

    try {
      const formData = new FormData()
      formData.append('file', file)
      let fullPath = prefix + uploadPath
      if (uploadPath && !uploadPath.endsWith('/')) {
        fullPath += '/'
      }
      formData.append('prefix', fullPath)

      const xhr = new XMLHttpRequest()

      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
          setUploadProgress(Math.round((e.loaded / e.total) * 100))
        }
      })

      xhr.addEventListener('load', () => {
        if (xhr.status === 200) {
          fetchFiles(null, prefix)
          e.target.value = ''
          setUploadPath('')
        } else {
          setError(`Upload failed: ${xhr.status}`)
        }
        setUploading(false)
        setUploadProgress(0)
      })

      xhr.addEventListener('error', () => {
        setError('Upload failed')
        setUploading(false)
        setUploadProgress(0)
      })

      xhr.open('POST', `${API_BASE_URL}/files`)
      xhr.send(formData)
    } catch (err) {
      setError(err.message)
      setUploading(false)
      setUploadProgress(0)
    }
  }

  const handleDownload = (key) => {
    window.open(`${API_BASE_URL}/files/${encodeURIComponent(key)}/download`, '_blank')
  }

  const handleDeleteDirectory = async (prefix) => {
    const confirmMsg = `Delete directory "${prefix}" and ALL files inside?`
    if (!confirm(confirmMsg)) {
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await fetch(
        `${API_BASE_URL}/directories?${new URLSearchParams({ prefix })}`,
        { method: 'DELETE' }
      )

      if (!response.ok) {
        throw new Error(`Failed to delete directory: ${response.status}`)
      }

      const result = await response.json()
      alert(`Deleted ${result.deleted_count} file(s)`)
      fetchFiles(null, prefix.split('/').slice(0, -2).join('/') + '/')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleLoadMore = () => {
    if (nextToken) {
      fetchFiles(nextToken)
    }
  }

  const formatSize = (bytes) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
  }

  const formatDate = (isoString) => {
    return new Date(isoString).toLocaleString()
  }

  return (
    <div className="app">
      <header className="header">
        <h1>File Browser</h1>
        <p className="api-url">Connected to: {API_BASE_URL}</p>
      </header>

      <form onSubmit={handleSearch} className="search-form">
        <input
          type="text"
          placeholder="Filter by prefix (e.g., folder/subfolder/)"
          value={prefix}
          onChange={(e) => setPrefix(e.target.value)}
          className="search-input"
        />
        <button type="submit" disabled={loading} className="search-button">
          Search
        </button>
      </form>

      {error && (
        <div className="error">
          Error: {error}
        </div>
      )}

      {loading && files.length === 0 && directories.length === 0 && (
        <div className="loading">Loading...</div>
      )}

      {files.length === 0 && directories.length === 0 && !loading && !error && (
        <div className="empty">No files or directories found</div>
      )}

      <div className="upload-section">
        <div className="upload-controls">
          <div className="upload-path-container">
            <span className="upload-path-prefix">{prefix || '/'}</span>
            <input
              type="text"
              placeholder="subdir/ or subdir/file.txt"
              value={uploadPath}
              onChange={(e) => setUploadPath(e.target.value)}
              className="upload-path-input"
              disabled={uploading}
            />
          </div>
          <label className="upload-button">
            <input
              type="file"
              onChange={handleUpload}
              disabled={uploading}
              style={{ display: 'none' }}
            />
            {uploading ? `Uploading... ${uploadProgress}%` : 'Choose File'}
          </label>
        </div>
        {uploadPath && (
          <div className="upload-hint">
            Will upload to: {prefix}{uploadPath}
          </div>
        )}
        {uploading && (
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${uploadProgress}%` }}></div>
          </div>
        )}
      </div>

      {(files.length > 0 || directories.length > 0) && (
        <>
          {prefix && (
            <div className="breadcrumb">
              <button onClick={handleGoUp} className="breadcrumb-button">
                ← Go up
              </button>
              <span className="current-path">/{prefix}</span>
            </div>
          )}

          <div className="file-count">
            Showing {directories.length} director{directories.length !== 1 ? 'ies' : 'y'}, {files.length} file{files.length !== 1 ? 's' : ''}
          </div>

          <table className="file-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Size</th>
                <th>Last Modified</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {directories.map((dir) => (
                <tr key={dir.prefix} className="directory-row">
                  <td className="file-name directory-name" onClick={() => handleNavigate(dir.prefix)}>
                    📁 {dir.prefix}
                  </td>
                  <td className="file-size">-</td>
                  <td className="file-date">-</td>
                  <td className="file-actions">
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleDeleteDirectory(dir.prefix)
                      }}
                      className="action-button delete-button"
                      title="Delete directory"
                    >
                      🗑
                    </button>
                  </td>
                </tr>
              ))}
              {files.map((file) => (
                <tr key={file.key + file.etag}>
                  <td className="file-name">📄 {file.key}</td>
                  <td className="file-size">{formatSize(file.size)}</td>
                  <td className="file-date">{formatDate(file.last_modified)}</td>
                  <td className="file-actions">
                    <button
                      onClick={() => handleDownload(file.key)}
                      className="action-button download-button"
                      title="Download"
                    >
                      ⬇
                    </button>
                    <button
                      onClick={() => handleDelete(file.key)}
                      className="action-button delete-button"
                      title="Delete"
                    >
                      🗑
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {nextToken && (
            <div className="load-more">
              <button onClick={handleLoadMore} disabled={loading} className="load-more-button">
                {loading ? 'Loading...' : 'Load More'}
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}

export default App
