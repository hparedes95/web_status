# 07 — Catálogo de indicadores

Un **servicio** es "Azure". Un **indicador** es una señal concreta con fuente, umbral y
consecuencia. Este documento lista los indicadores candidatos ordenados por prioridad.

## La regla que decide si un indicador entra

> **¿Qué haría yo distinto si este indicador se pone en rojo?**

Si la respuesta es "nada" o "mirarlo", el indicador no entra. Un panel con 60 luces es
un panel que nadie lee. La disciplina de esta pregunta es lo que separa un panel útil de
un árbol de Navidad.

Cada indicador se define con cinco campos:

| Campo | Ejemplo |
|---|---|
| **Qué mide** | Autenticación contra Entra ID desde nuestra red |
| **Fuente** | Sonda propia (OAuth client credentials cada 5 min) |
| **Umbral** | 2 fallos consecutivos → rojo |
| **Acción** | Avisar a sistemas; no abrir incidencia con el proveedor hasta confirmar con el feed |
| **Esfuerzo** | S (≤ 0,5 d) · M (0,5–1,5 d) · L (> 1,5 d) |

---

## A. Microsoft 365 — prioridad 1

Fuente principal: **Microsoft Graph**, `serviceAnnouncement`. Da el estado de *nuestro
tenant*, no el global, que es lo que de verdad queremos. Un único adaptador (M) sirve
para todos los indicadores de este bloque; a partir de ahí, cada servicio nuevo es
añadir una línea al YAML.

| # | Indicador | Fuente | Esfuerzo | Por qué importa |
|---|---|---|---|---|
| A1 | **Entra ID / identidad** | Graph | S | Si cae, no se entra a *nada*. Es el indicador con más consecuencias del catálogo y el que más gente da por supuesto |
| A2 | **Exchange Online** (correo) | Graph | S | La primera queja que llega siempre |
| A3 | **Microsoft Teams** | Graph | S | Chat, llamadas y reuniones a la vez |
| A4 | **SharePoint / OneDrive** | Graph | S | Ficheros; cuando falla, la gente cree que ha perdido su trabajo |
| A5 | **Intune** | Graph | S | Solo si gestionáis dispositivos con él |
| A6 | **Microsoft 365 Copilot** | Graph | S | Encaja aquí, no en el bloque de IA |
| A7 | **Power Platform** | Graph | S | Solo si hay Power BI o Power Automate en producción |
| A8 | **Incidencia activa con su ID** (`EX123456`, `TM123456`) | Graph | S | Mostrarlo permite buscar el aviso oficial y citarlo al usuario que pregunta |
| A9 | **Mensajes del Centro de Mensajes** | Graph `serviceAnnouncement/messages` | M | **Muy infravalorado**: avisa con semanas de antelación de cambios que van a romper algo. No es un semáforo, es una bandeja de "esto te va a afectar" |
| A10 | **Sonda de login real** | Propia: petición OAuth cada 5 min | M | Detecta antes que el feed, y detecta problemas que solo nos afectan a nosotros (una directiva de acceso condicional mal puesta el viernes por la tarde) |
| A11 | **Sonda de correo extremo a extremo** | Propia: enviar a un buzón de pruebas y medir la entrega | L | Detecta *colas* de Exchange, que el feed no reporta nunca. Caro pero es el indicador más honesto del bloque |
| A12 | **Sincronización de Entra Connect** | Propia o Graph | M | Si la sincronización se para, las contraseñas dejan de propagarse. Nadie lo nota hasta que alguien no puede entrar. Umbral: última sincronización > 60 min |

> **Recomendación:** A1–A4 y A8 en la primera tanda (son la misma integración). A9 y A10
> en cuanto el panel esté en marcha: son los dos que aportan algo que hoy no tenéis.

---

## B. Azure — prioridad 1

Hay tres fuentes distintas y conviene no mezclarlas: el estado global (público), los
eventos que afectan a **nuestra suscripción** (Service Health) y el estado de **cada
recurso** (Resource Health).

| # | Indicador | Fuente | Esfuerzo | Por qué importa |
|---|---|---|---|---|
| B1 | **Estado global por región** (filtrado a las nuestras) | RSS público | S | Filtrar por región es imprescindible: una caída en Brasil no puede poner rojo el panel |
| B2 | **Incidencias que afectan a nuestra suscripción** | Service Health, tipo *Service issue* | M | La diferencia entre "Azure tiene un problema" y "Azure tiene un problema que nos toca" |
| B3 | **Mantenimientos programados sobre nuestros recursos** | Service Health, tipo *Planned maintenance* | S | Explica el reinicio de la VM del martes que nadie sabía de dónde venía |
| B4 | **Avisos de salud y deprecaciones** | Service Health, tipo *Health advisory* | S | Acciones con fecha límite: versiones que se retiran, TLS que se deja de admitir |
| B5 | **Avisos de seguridad** | Service Health, tipo *Security advisory* | S | Poco frecuentes, muy importantes |
| B6 | **Recursos no disponibles** (contador) | Resource Health | M | Un único número: "3 de 47 recursos no disponibles". Cuando pasa de 0, hay algo que mirar |
| B7 | **VPN / ExpressRoute hacia Azure** | Sonda propia desde la red | M | Distingue "Azure caído" de "no llegamos a Azure", que es un fallo nuestro y se arregla distinto |
| B8 | **Certificados y secretos de Key Vault que caducan** | Azure API | M | Caída autoinfligida clásica. Umbral: 30 / 14 / 7 días |

---

## C. AWS — prioridad 1

| # | Indicador | Fuente | Esfuerzo | Por qué importa |
|---|---|---|---|---|
| C1 | **Estado por servicio y región** (`eu-west-1`, `eu-south-2`…) | Health Dashboard público | M | Igual que en Azure: sin filtro de región el indicador es ruido |
| C2 | **Eventos de nuestra cuenta** | AWS Health API | M | ⚠️ **Requiere plan de soporte Business o Enterprise.** Comprobarlo antes de estimarlo; si no lo hay, solo queda el público |
| C3 | **Sonda a nuestros propios recursos en AWS** | Propia | S | Lo mismo que B7: separa "AWS" de "nuestro camino hasta AWS" |

> Si en AWS solo tenéis un par de cosas, C1 filtrado a vuestra región puede ser
> suficiente y C2 no compensa. Merece la pena mirar qué hay desplegado antes de decidir.

---

## D. Telefonía y conectividad — prioridad 2

**Aquí no hay feeds, y hay que ser claro sobre qué se puede medir de verdad.**

Aviso previo: *Movistar es la marca comercial de Telefónica* — es un indicador, no dos.
Y antes de dar por bueno un respaldo móvil, **comprobad sobre qué red circula en
realidad**: varios operadores usan la red de otro. Un respaldo que va por la misma red
que la línea principal no es un respaldo, y eso solo se descubre el día que hace falta.

| # | Indicador | Fuente | Esfuerzo | Realidad |
|---|---|---|---|---|
| D1 | **Línea de internet por sede, con salto culpable** | Sonda propia: gateway → DNS del operador → destino externo | M | El indicador estrella. El primer salto que falla dice si es el router, el operador o internet |
| D2 | **Caída del operador vs. caída nuestra** (derivado) | Correlación entre sedes del mismo operador | S | Si tres sedes con el mismo operador caen a la vez, es del operador. Sale gratis si ya tenéis D1 en varias sedes |
| D3 | **Red móvil de cada operador** | Router o Raspberry Pi con SIM de datos haciendo ping | M | **La única forma real de medir esto.** ~5 €/mes por SIM y operador. Si ya hay un router 4G/5G de respaldo, ya está medio hecho |
| D4 | **Estado del respaldo 4G/5G** | Sonda a través de la interfaz de respaldo | S | Un respaldo que no se prueba nunca no es un respaldo. Comprobarlo semanalmente aunque no esté en uso |
| D5 | **Registro SIP / centralita** | Sonda al registro SIP y llamada de prueba | M | Si hay centralita VoIP, esto *es* "telefonía" para el usuario, y falla más que la red móvil |
| D6 | **Cobertura móvil en la oficina** | Manual | S | Ojo: una antena concreta puede estar mal sin que el operador tenga una caída nacional. Son cosas distintas y el panel debe decirlo |
| D7 | **Avería declarada por el operador** | Manual, con autor y hora | S | Cuando alguien llama al soporte y le confirman la avería, ese dato vale y hay que poder registrarlo |
| D8 | **Latencia y pérdida de paquetes de la línea** | Sonda propia | S | La degradación es más frecuente que la caída, y es la que provoca "Teams se me corta" |

---

## E. Energía y sala técnica — prioridad 3

El corte de luz es solo una parte. **El aire acondicionado del CPD falla más a menudo
que el suministro eléctrico**, y con consecuencias parecidas.

| # | Indicador | Fuente | Esfuerzo | Por qué importa |
|---|---|---|---|---|
| E1 | **Alimentación de red presente / en batería** | SNMP del SAI | M | El indicador de energía de verdad. Requiere que el SAI tenga tarjeta de red |
| E2 | **Autonomía restante en minutos** | SNMP del SAI | S | El único número que importa durante un corte: decide si hay que empezar a apagar |
| E3 | **Salud y carga de la batería** | SNMP del SAI | S | Una batería al 60 % de salud te da la mitad de autonomía de la que crees tener |
| E4 | **Microcortes: transferencias a batería por mes** | Derivado de E1 | S | Si se repiten, hay un problema de calidad de suministro. Contarlos da argumentos para reclamar |
| E5 | **Temperatura de la sala técnica** | Sonda de temperatura o SNMP del climatizador | M | Falla más que la luz y avisa con horas de margen si se mide |
| E6 | **Consumo por fase del rack** | PDU gestionable | M | Detecta un desequilibrio antes de que salte el diferencial |
| E7 | **Grupo electrógeno: estado y combustible** | SNMP o manual | M | Solo si lo hay |
| E8 | **Corte de la distribuidora** | Manual | S | Las distribuidoras (e-distribución, i-DE, UFD…) publican mapas de incidencias, pero no API |

> **Descartado:** los datos de demanda en tiempo real de Red Eléctrica. Son interesantes,
> pero no dicen nada sobre si vuestro edificio tiene luz. Es un indicador bonito e inútil,
> del tipo que llena paneles.

---

## F. Inteligencia artificial — prioridad 4 (secundaria)

Para las IA, **la caída total es lo raro; lo normal es la degradación**. Por eso la página
de estado sirve de poco y la sonda sintética sirve de mucho: una llamada real y mínima
cada 5 minutos cuesta céntimos al mes y detecta lo que el feed no cuenta.

| # | Indicador | Fuente | Esfuerzo | Nota |
|---|---|---|---|---|
| F1 | **Claude (Anthropic)** | Statuspage | S | El adaptador genérico ya lo cubre |
| F2 | **ChatGPT / API de OpenAI** | Statuspage | S | Distinguir la web del API: pueden fallar por separado |
| F3 | **GitHub Copilot** | Componente de GitHub | S | Filtrar por componente: que no se ponga rojo porque falle GitHub Pages |
| F4 | **Microsoft 365 Copilot** | Graph → ver A6 | — | Va con el bloque de Microsoft |
| F5 | **Gemini / Vertex AI** | Estado de Google Cloud | M | Solo si se usa |
| F6 | **Latencia p95 de las APIs que consumimos** | Sonda sintética | M | El indicador honesto: "responde, pero tarda el triple" |
| F7 | **Errores 429 (límite de tasa)** | Sonda o nuestros propios logs | S | Distingue "el proveedor está mal" de "nos hemos pasado de cuota", que se arregla de forma completamente distinta |
| F8 | **Caducidad de claves de API y saldo** | Manual o API del proveedor | M | Falla el día menos pensado y no aparece en ninguna página de estado |

---

## G. Los que no has pedido y probablemente te salven un día

Estos no son caídas de proveedor: son **caídas autoinfligidas y previsibles**. Casi todos
son sondas de bajo coste y avisan con semanas de antelación.

| # | Indicador | Esfuerzo | Por qué |
|---|---|---|---|
| G1 | **Certificados TLS a punto de caducar** | S | La caída evitable más común que existe. Umbrales 30 / 14 / 7 días. Media jornada de trabajo |
| G2 | **Dominios a punto de caducar** | S | Consulta WHOIS mensual. Ha tumbado empresas enteras durante días |
| G3 | **Resolución DNS de nuestros dominios desde fuera** | S | Si el DNS externo falla, la web y el correo desaparecen aunque todo esté encendido. Se mide desde el recolector, que ya está fuera |
| G4 | **Nuestras IP de salida en listas negras de correo** | M | Dejas de poder enviar correo y **nadie te avisa**: los rebotes se los queda el destinatario. Consulta a Spamhaus y similares |
| G5 | **La web pública propia, vista desde fuera** | S | Disponibilidad y tiempo de carga, medidos desde donde está el cliente |
| G6 | **ERP y aplicaciones de negocio propias** | M | Una sonda HTTP a una página de salud. Para el usuario, "el sistema" es esto, no Azure |
| G7 | **Túneles VPN entre sedes** | M | Estado y latencia de cada túnel |
| G8 | **Servicios de la Administración** (AEAT, Seguridad Social, FNMT, Cl@ve) | M | Si hay que presentar impuestos o firmar digitalmente, sus caídas son vuestro problema. Sonda HTTP simple, sin API |
| G9 | **Pasarela de pago** (Redsys, Stripe…) | S | Si se cobra en línea, esto es facturación perdida por minuto |
| G10 | **GitHub / GitLab** | S | Statuspage; el adaptador genérico ya lo cubre |
| G11 | **Licencias que caducan** (antivirus, copias, virtualización) | M | Aviso a 60 días. Evita la renovación de urgencia a precio de urgencia |
| G12 | **Última copia de seguridad correcta** | M | ⚠️ Frontera de alcance (ver más abajo), pero es el fallo silencioso que más caro sale |

---

## H. Indicadores derivados — casi gratis, muy útiles

Se calculan con datos que el sistema ya tiene. Añaden mucho por poco.

| # | Indicador | Para qué |
|---|---|---|
| H1 | **Cuántos servicios no están operativos** | El titular del panel. Es lo único que se lee desde tres metros |
| H2 | **Frescura del dato por fuente** | "Hace 3 min" en cada tarjeta. Es la defensa contra el riesgo R2 (falsa sensación de seguridad) |
| H3 | **Tiempo transcurrido desde el inicio de la incidencia** | "Caído desde hace 34 min". Lo que se pega en el correo a dirección |
| H4 | **Discrepancia feed / sonda** | "El proveedor dice que está bien, nosotros no llegamos". Es la señal más valiosa del sistema |
| H5 | **Ranking mensual de proveedores por minutos caídos** | Munición objetiva para la renovación del contrato |
| H6 | **Servicios sin incidencias en 90 días** | Candidatos a quitar del panel. Ayuda a que no crezca sin control |

---

## Frontera de alcance

Estos indicadores son útiles, pero pertenecen a una herramienta de monitorización
(Zabbix, PRTG, Grafana), no a un panel de estado de proveedores. Si entran, el proyecto
pasa de 22 días a 60 y deja de terminarse:

- CPU, memoria y disco de servidores
- Estado de las copias de seguridad más allá de "la última fue correcta" (G12)
- Salud de cabinas, hipervisores y switches
- Logs de aplicación y trazas

**Criterio:** este panel responde a *"¿está caído algo de lo que dependemos?"*.
No responde a *"¿por qué va lento nuestro servidor?"*.

---

## Primera tanda recomendada (15 indicadores)

Con esto se cubre lo que preguntas al 90 %, y cabe en las fases 1 a 3 del plan:

| Prioridad | Indicadores | Bloque |
|---|---|---|
| 1 | Entra ID, Exchange, Teams, SharePoint, Copilot M365 | A1–A4, A6 |
| 1 | Azure: nuestra suscripción + mantenimientos programados | B2, B3 |
| 1 | AWS: estado de nuestra región | C1 |
| 2 | Internet por sede con salto culpable | D1 |
| 2 | Red móvil del operador de respaldo | D3 |
| 3 | SAI: alimentación de red y autonomía restante | E1, E2 |
| 4 | Claude, ChatGPT, GitHub Copilot | F1–F3 |
| — | Certificados TLS a punto de caducar | G1 |

Y dos derivados que salen gratis: **cuántos servicios no están operativos** (H1) y
**frescura del dato** (H2).

Lo demás entra después, y solo si sobrevive a la pregunta: *¿qué haría yo distinto si
esto se pone en rojo?*
