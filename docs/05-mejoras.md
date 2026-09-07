# 05 — Qué añadir a continuación

Propuesta ordenada por **valor entre esfuerzo**, pensada para lo que sois: una empresa de
software con servidores propios y con Azure.

El filtro sigue siendo el mismo de siempre: *¿qué haría yo distinto si esto se pone en
rojo?* Si la respuesta es «nada», no entra.

---

## Ya está construido, solo hay que encenderlo

### 1. Vuestros propios servicios y sus certificados · **15 min**

Ya hay adaptador (`tipo: http`), con los bloques comentados en `services.yaml`. Para una
empresa de software **esto es lo que ve el cliente**, así que probablemente sea el
indicador más importante de todo el panel — y ahora mismo no está.

De regalo vigila la **caducidad del certificado TLS**, que es la caída autoinfligida más
común que existe y la más fácil de evitar.

---

## Alto valor, poco esfuerzo

### 2. Los registros de paquetes · **10 min** ⭐

Si se cae npm, PyPI o Docker Hub, **no se construye ni se despliega nada**. Es una parada
real de vuestro trabajo y casi nadie lo tiene en el panel. Fuentes ya comprobadas:

| Servicio | Fuente | Comprobado |
|---|---|---|
| npm | `status.npmjs.org` | ✅ HTTP 200, formato estándar |
| PyPI / Python | `status.python.org` | ✅ HTTP 200, formato estándar |
| Docker Hub | `www.dockerstatus.com` | ✅ HTTP 200, formato estándar |
| HashiCorp (Terraform, Vault) | `status.hashicorp.com` | ✅ HTTP 200, formato estándar |
| NuGet | `status.nuget.org` | ❌ 404 en esa ruta: hay que buscar la buena |

Los cuatro que funcionan son **una línea de configuración cada uno**, sin desarrollo.

### 3. Azure Service Health de vuestra suscripción · **1 día** ⭐

Hoy el panel lee el **RSS global de Azure**: dice si Azure tiene un problema en el mundo,
no si lo tiene en *vuestros* recursos. Con un service principal (el mismo patrón que ya
está escrito para Microsoft Graph) se obtiene:

- Las incidencias que **os afectan a vosotros**, no las de Brasil.
- **Mantenimientos programados sobre vuestros recursos** — lo que explica el reinicio de la
  VM del martes que nadie sabía de dónde salía.
- Avisos de deprecación con fecha límite.

Trabajando con Azure, esta es la mejora de más calidad de toda la lista.

### 4. Dominios y DNS · **medio día**

- **Dominios a punto de caducar**: una consulta al mes. Ha tumbado empresas enteras durante
  días, y siempre por lo mismo.
- **Resolución DNS desde fuera**: si vuestro DNS externo falla, la web y el correo
  desaparecen aunque todo esté encendido. Se mide desde el runner, que ya está fuera.

### 5. Listas negras de correo · **medio día**

Si vuestras aplicaciones mandan correo (avisos, altas, recuperación de contraseña), que la
IP de salida entre en una lista negra significa **dejar de entregar sin que nadie avise**:
los rebotes se los queda el destinatario. Se detecta consultando Spamhaus y similares.

---

---

## Mejoras del panel

| Mejora | Esfuerzo | Para qué |
|---|---|---|
| **Ventanas de mantenimiento** | medio día | Silenciar alertas durante un despliegue previsto, en vez de que la gente aprenda a ignorarlas |
| **Informe semanal por Telegram** | medio día | Minutos caídos por proveedor. Munición objetiva para renovar contratos |
| **Modo pantalla grande** | 2 h | Para un monitor en la oficina, sin interacción |
| **Histórico de incidencias navegable** | 1 día | Hoy hay 72 h de barras; poder mirar «qué pasó el martes» es otra cosa |
| **Agrupar por criticidad** | 2 h | Que lo crítico salga arriba aunque sea de otra categoría |

---

## Dónde NO ir

Esto pertenece a una herramienta de monitorización (Zabbix, Grafana, Application Insights),
no a un panel de estado. Si entra, el proyecto deja de terminarse:

- CPU, memoria y métricas de rendimiento de servidores
- Logs, trazas y APM de vuestras aplicaciones
- Salud de cabinas, hipervisores y electrónica de red
- Colas y rendimiento de bases de datos

**El criterio:** este panel responde a *«¿está caído algo de lo que dependemos?»*.
No responde a *«¿por qué va lento nuestro servidor?»*. En cuanto empiece a responder a la
segunda, dejará de responder bien a la primera.

---

## Si tuviera que elegir tres

1. **Vuestras propias APIs y webs** (§1) — es lo que ve el cliente y no está.
2. **Los registros de paquetes** (§2) — diez minutos, y cubre una parada real de trabajo.
3. **El certificado TLS** — va de regalo con §1 y evita la caída autoinfligida más común.

Con eso, en una tarde, el panel pasa de «qué dicen los proveedores» a «cómo estamos
nosotros», que es la pregunta que de verdad se hace la gente.
