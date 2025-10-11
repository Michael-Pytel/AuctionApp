# AuctionApp - Production Django Auction Platform

A Django 5.1 auction platform with real-time bidding, deployed on Google Cloud Platform with production-grade infrastructure.

**Live Demo**: [AuctionApp - link](michalpytel.com.pl)

---

## 🏗️ Production Architecture

```
Internet Request
    ↓
Nginx (Reverse Proxy)
    ├── Static file serving with far-future cache headers
    ├── Request buffering and SSL termination
    └── Unix socket proxy to ↓
    
Gunicorn (3 Workers)
    └── Forwards to ↓
    
Django Application
    └── Database connection via ↓
    
Cloud SQL Proxy
    ├── Encrypted tunnel (eliminates public DB IP)
    ├── IAM-based authentication
    └── Connects to Cloud SQL PostgreSQL
```

### Key Architectural Decisions

**Why Nginx as Reverse Proxy?**
- Static files served directly without touching Django (70% bandwidth reduction)
- Request buffering prevents slow clients from blocking app workers
- Enables future horizontal scaling with load balancing

**Why Cloud SQL Proxy?**
- No public database IP needed (security layer)
- Automatic encryption without manual SSL certificate management
- Handles IAM authentication and automatic credential rotation
- Connection pooling and automatic reconnection on network issues

**Why Unix Sockets over TCP?**
- Lower latency (no TCP/IP stack overhead)
- Better performance for local inter-process communication
- Automatic access control via filesystem permissions

**Why 3 Gunicorn Workers?**
- Formula: `(2 x CPU_cores) + 1` = optimal for e2-micro (1 vCPU)
- Balances concurrency with memory constraints
- Prevents resource exhaustion under load

---

## 🔐 Security Implementation

### Infrastructure Security
- **Cloud SQL Proxy Tunnel**: Database connections never exposed to public internet
- **GCP Secret Manager**: Credentials stored encrypted, never in code or config files
- **Systemd Process Isolation**: Application runs as dedicated user (not root)
- **Environment-based Configuration**: Separation of dev/prod secrets via python-decouple

### Application Security
- **Rate Limiting on Bids**: 10 bids/minute prevents auction manipulation
- **Email Verification**: Token-based confirmation with 24-hour expiration
- **Self-bidding Prevention**: Business logic enforces auction integrity
- **Password Requirements**: 8+ chars, mixed case, numbers, special characters enforced server-side

### Production Settings
```python
# Security headers automatically added in production
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
X_FRAME_OPTIONS = 'DENY'
```

---

## 🚀 Deployment Stack

**Infrastructure**: GCP Compute Engine (e2-micro, Ubuntu 22.04) + Cloud SQL PostgreSQL 15  
**Web Stack**: Nginx → Gunicorn (3 workers) → Django 5.1  
**Database Connection**: Cloud SQL Proxy (encrypted tunnel)  
**Static Files**: WhiteNoise (gzip compression, immutable caching)  
**Process Management**: Systemd services with auto-restart  
**Email**: SendGrid transactional email  

---

## 📊 Technical Highlights

### Database Architecture
**PostgreSQL over SQLite** for production:
- Proper concurrent access with row-level locking
- Connection pooling (`CONN_MAX_AGE=600`)
- Query optimization with indexes on frequently accessed fields
- ACID compliance for auction bid integrity

### Static File Optimization
**WhiteNoise Configuration**:
- Automatic compression (reduces file sizes by ~70%)
- Immutable caching with far-future expiry headers
- Manifest-based versioning for cache busting
- No CDN required for medium traffic loads

### Process Management
**Systemd Service Architecture**:
```ini
# Three automated services with dependency ordering
cloudsql-proxy.service (After=network.target)
    └── Provides database connectivity
gunicorn.service (After=network.target)
    └── Application server with auto-restart
nginx.service
    └── Reverse proxy and static serving
```

All services configured with `Restart=always` for automatic recovery from failures.

---

## 🔧 Key Technical Challenges Solved

### 1. Cloud SQL Proxy Configuration
**Challenge**: Service failing with exit code 2  
**Root Cause**: Incompatible flag syntax between proxy versions  
**Solution**: Updated to correct `-instances=PROJECT:REGION:INSTANCE=tcp:5432` format, switched to TCP over Unix socket for reliability

### 2. PostgreSQL Schema Permissions
**Challenge**: Django migrations failing with "permission denied for schema public"  
**Solution**: Granted schema ownership and default privileges:
```sql
ALTER SCHEMA public OWNER TO auction_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO auction_user;
```

### 3. Static File Delivery
**Challenge**: CSS/JS files returning 404 in production  
**Solution**: Implemented WhiteNoise middleware and configured Nginx location blocks with proper aliasing and caching headers

---

## 🗃️ Database Schema Design

**Core Models**:
- **Custom User Model** (extends AbstractUser): Email verification workflow with token expiration
- **Listing**: Auction items with category relationships and active/inactive status
- **Bid**: Timestamped bid history with amount validation and highest bid tracking
- **Watchlist**: Many-to-many relationship for user favorites
- **Notification**: Winner alerts with read/unread status

**Key Relationships**:
- One-to-Many: User → Listings (owner)
- Many-to-Many: User ↔ Listings (watchlist)
- One-to-Many: Listing → Bids (history)
- Foreign Keys with `on_delete=CASCADE` for referential integrity

---

## 🎓 Technical Skills Demonstrated

### Cloud Infrastructure
- GCP resource provisioning (Compute Engine, Cloud SQL, Secret Manager)
- Secure database connectivity with Cloud SQL Proxy
- Credential management and secret rotation
- Automated backup configuration

### System Architecture
- Reverse proxy implementation and request routing
- WSGI server configuration and worker tuning
- Unix socket inter-process communication
- Systemd service orchestration

### DevOps
- Linux server administration (Ubuntu)
- Service monitoring with journalctl
- Environment-based configuration management
- Production deployment workflows

---

## 🔮 Scalability Path

**Current**: Single VM with all components  
**Next Steps**:
- **Horizontal Scaling**: Managed Instance Group with load balancer
- **Caching Layer**: Redis for session storage and query caching
- **Background Tasks**: Celery for async email sending
- **Read Replicas**: Cloud SQL read replicas for query distribution
- **CDN**: Cloud CDN for global static file distribution

---

## 👤 Author

**Michal Pytel**  
[GitHub](https://github.com/Michael-Pytel) | [LinkedIn](https://www.linkedin.com/in/michael-g-pytel/)

*Production Django deployment on Google Cloud Platform*
