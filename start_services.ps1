# Verificar e iniciar Redis en Docker
Write-Host "Verificando contenedor de Redis..." -ForegroundColor Cyan
$redisCheck = docker ps -a --filter "name=redis-broker" --format "{{.Status}}"
if ($redisCheck -like "*Up*") {
    Write-Host "Redis ya está corriendo." -ForegroundColor Green
} elseif ($redisCheck) {
    Write-Host "Iniciando contenedor Redis existente (redis-broker)..." -ForegroundColor Yellow
    docker start redis-broker
} else {
    Write-Host "Creando e iniciando contenedor Redis (redis-broker)..." -ForegroundColor Yellow
    docker run -d --name redis-broker -p 6379:6379 redis
}

# Iniciar Celery Worker en una nueva ventana
Write-Host "Lanzando Celery Worker en una nueva ventana..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "$Host.UI.RawUI.WindowTitle = 'Celery Worker'; Write-Host 'Cargando Celery Worker...' -ForegroundColor Cyan; poetry run celery -A celery_app worker --loglevel=info --pool=solo"

# Iniciar Folder Watcher en una nueva ventana
Write-Host "Lanzando Folder Watcher en una nueva ventana..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "$Host.UI.RawUI.WindowTitle = 'Folder Watcher'; Write-Host 'Cargando Vigilante de Carpeta...' -ForegroundColor Cyan; poetry run python watcher.py"

Write-Host "==========================================================" -ForegroundColor Green
Write-Host "¡Entorno de sincronización e ingesta iniciado con éxito!" -ForegroundColor Green
Write-Host "Las ventanas de Celery y Watcher están abiertas y corriendo." -ForegroundColor Green
Write-Host "Ya puedes soltar archivos en la carpeta configurada." -ForegroundColor Green
Write-Host ""
Write-Host "Puedes hacer preguntas al RAG en esta misma terminal usando:" -ForegroundColor Green
Write-Host "  poetry run python main.py 'Tu pregunta'" -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Green
