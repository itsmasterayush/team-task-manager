import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask_cors import CORS

app = Flask(__name__, static_folder='../frontend', static_url_path='/')
# Enable CORS for the frontend to communicate with the backend
CORS(app)

# Use SQLite for local development, and an environment variable for production (e.g., Railway PostgreSQL)
database_url = os.environ.get('DATABASE_URL', 'sqlite:///taskmanager.db')
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'super-secret-key-12345')

db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='MEMBER') # 'ADMIN' or 'MEMBER'

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    owner = db.relationship('User', backref=db.backref('owned_projects', lazy=True))

class ProjectMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    project = db.relationship('Project', backref=db.backref('members', cascade="all, delete-orphan", lazy=True))
    user = db.relationship('User', backref=db.backref('project_memberships', cascade="all, delete-orphan", lazy=True))

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='TODO') # 'TODO', 'IN_PROGRESS', 'DONE'
    due_date = db.Column(db.DateTime, nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    assignee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    project = db.relationship('Project', backref=db.backref('tasks', cascade="all, delete-orphan", lazy=True))
    assignee = db.relationship('User', backref=db.backref('assigned_tasks', lazy=True))

# Create tables
with app.app_context():
    db.create_all()

# Authentication Middleware
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            parts = request.headers['Authorization'].split()
            if len(parts) == 2 and parts[0] == 'Bearer':
                token = parts[1]
        
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
            
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.get(data['user_id'])
            if not current_user:
                return jsonify({'message': 'User not found!'}), 401
        except Exception as e:
            return jsonify({'message': 'Token is invalid!'}), 401
            
        return f(current_user, *args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(current_user, *args, **kwargs):
        if current_user.role != 'ADMIN':
            return jsonify({'message': 'Admin privilege required!'}), 403
        return f(current_user, *args, **kwargs)
    return decorated

# API Routes

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password') or not data.get('name'):
        return jsonify({'message': 'Missing data'}), 400
        
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'message': 'User already exists'}), 400
        
    hashed_password = generate_password_hash(data['password'])
    role = data.get('role', 'MEMBER')
    if role not in ['ADMIN', 'MEMBER']:
        role = 'MEMBER'
        
    new_user = User(name=data['name'], email=data['email'], password=hashed_password, role=role)
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({'message': 'User created successfully'}), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'message': 'Missing data'}), 400
        
    user = User.query.filter_by(email=data['email']).first()
    if not user or not check_password_hash(user.password, data['password']):
        return jsonify({'message': 'Invalid credentials'}), 401
        
    token = jwt.encode({
        'user_id': user.id,
        'exp': datetime.now(timezone.utc) + timedelta(days=1)
    }, app.config['SECRET_KEY'], algorithm="HS256")
    
    return jsonify({
        'token': token, 
        'user': {'id': user.id, 'name': user.name, 'email': user.email, 'role': user.role}
    }), 200

@app.route('/api/users', methods=['GET'])
@token_required
def get_users(current_user):
    users = User.query.all()
    return jsonify([{'id': u.id, 'name': u.name, 'email': u.email, 'role': u.role} for u in users])

@app.route('/api/projects', methods=['GET'])
@token_required
def get_projects(current_user):
    # Admins see all projects, Members see projects they are part of
    if current_user.role == 'ADMIN':
        projects = Project.query.all()
    else:
        # Get projects where user is owner OR a member
        member_project_ids = [pm.project_id for pm in ProjectMember.query.filter_by(user_id=current_user.id).all()]
        projects = Project.query.filter((Project.owner_id == current_user.id) | (Project.id.in_(member_project_ids))).all()
        
    result = []
    for p in projects:
        members = [{'id': pm.user.id, 'name': pm.user.name} for pm in p.members]
        result.append({
            'id': p.id,
            'name': p.name,
            'description': p.description,
            'owner_id': p.owner_id,
            'members': members
        })
    return jsonify(result), 200

@app.route('/api/projects', methods=['POST'])
@token_required
@admin_required
def create_project(current_user):
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify({'message': 'Project name is required'}), 400
        
    new_project = Project(
        name=data['name'], 
        description=data.get('description', ''), 
        owner_id=current_user.id
    )
    db.session.add(new_project)
    db.session.commit()
    
    # Add owner as a member automatically
    db.session.add(ProjectMember(project_id=new_project.id, user_id=current_user.id))
    db.session.commit()
    
    return jsonify({'message': 'Project created', 'project_id': new_project.id}), 201

@app.route('/api/projects/<int:project_id>/members', methods=['POST'])
@token_required
@admin_required
def add_project_member(current_user, project_id):
    data = request.get_json()
    if not data or not data.get('user_id'):
        return jsonify({'message': 'User ID required'}), 400
        
    project = Project.query.get_or_404(project_id)
    user = User.query.get_or_404(data['user_id'])
    
    if ProjectMember.query.filter_by(project_id=project_id, user_id=user.id).first():
        return jsonify({'message': 'User is already a member'}), 400
        
    new_member = ProjectMember(project_id=project_id, user_id=user.id)
    db.session.add(new_member)
    db.session.commit()
    
    return jsonify({'message': 'Member added successfully'}), 200

@app.route('/api/tasks', methods=['GET'])
@token_required
def get_tasks(current_user):
    project_id = request.args.get('project_id')
    
    query = Task.query
    
    if project_id:
        # Check if user has access to this project
        if current_user.role != 'ADMIN':
            member = ProjectMember.query.filter_by(project_id=project_id, user_id=current_user.id).first()
            if not member and Project.query.get(project_id).owner_id != current_user.id:
                return jsonify({'message': 'Access denied'}), 403
        query = query.filter_by(project_id=project_id)
    else:
        # If no project specified, return tasks assigned to the user or all tasks if ADMIN
        if current_user.role != 'ADMIN':
            query = query.filter_by(assignee_id=current_user.id)
            
    tasks = query.all()
    result = []
    for t in tasks:
        result.append({
            'id': t.id,
            'title': t.title,
            'description': t.description,
            'status': t.status,
            'due_date': t.due_date.isoformat() if t.due_date else None,
            'project_id': t.project_id,
            'project_name': t.project.name,
            'assignee_id': t.assignee_id,
            'assignee_name': t.assignee.name if t.assignee else None
        })
    return jsonify(result), 200

@app.route('/api/tasks', methods=['POST'])
@token_required
def create_task(current_user):
    data = request.get_json()
    if not data or not data.get('title') or not data.get('project_id'):
        return jsonify({'message': 'Title and Project ID are required'}), 400
        
    project = Project.query.get_or_404(data['project_id'])
    
    # Only Admin or Project Owner can create tasks
    if current_user.role != 'ADMIN' and project.owner_id != current_user.id:
        return jsonify({'message': 'Only Admins can create tasks'}), 403
        
    due_date = None
    if data.get('due_date'):
        try:
            due_date = datetime.fromisoformat(data['due_date'].replace('Z', '+00:00'))
        except ValueError:
            pass

    new_task = Task(
        title=data['title'],
        description=data.get('description', ''),
        status=data.get('status', 'TODO'),
        due_date=due_date,
        project_id=project.id,
        assignee_id=data.get('assignee_id')
    )
    db.session.add(new_task)
    db.session.commit()
    
    return jsonify({'message': 'Task created', 'task_id': new_task.id}), 201

@app.route('/api/tasks/<int:task_id>', methods=['PATCH'])
@token_required
def update_task(current_user, task_id):
    task = Task.query.get_or_404(task_id)
    
    # Admin can update anything. Members can only update status of their assigned tasks
    if current_user.role != 'ADMIN':
        if task.assignee_id != current_user.id:
            return jsonify({'message': 'You can only update your assigned tasks'}), 403
            
    data = request.get_json()
    
    if current_user.role == 'ADMIN':
        if 'title' in data: task.title = data['title']
        if 'description' in data: task.description = data['description']
        if 'assignee_id' in data: task.assignee_id = data['assignee_id']
        if 'due_date' in data:
            if data['due_date']:
                task.due_date = datetime.fromisoformat(data['due_date'].replace('Z', '+00:00'))
            else:
                task.due_date = None

    if 'status' in data:
        if data['status'] in ['TODO', 'IN_PROGRESS', 'DONE']:
            task.status = data['status']
            
    db.session.commit()
    return jsonify({'message': 'Task updated successfully'}), 200

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
@token_required
@admin_required
def delete_task(current_user, task_id):
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    return jsonify({'message': 'Task deleted successfully'}), 200

@app.route('/api/dashboard', methods=['GET'])
@token_required
def get_dashboard(current_user):
    query = Task.query
    if current_user.role != 'ADMIN':
        query = query.filter_by(assignee_id=current_user.id)
        
    tasks = query.all()
    
    total = len(tasks)
    todo = sum(1 for t in tasks if t.status == 'TODO')
    in_progress = sum(1 for t in tasks if t.status == 'IN_PROGRESS')
    done = sum(1 for t in tasks if t.status == 'DONE')
    
    now = datetime.now(timezone.utc)
    # To handle offset-naive and offset-aware datetimes safely
    overdue = sum(1 for t in tasks if t.due_date and t.status != 'DONE' and t.due_date.replace(tzinfo=timezone.utc) < now)
    
    return jsonify({
        'total': total,
        'todo': todo,
        'in_progress': in_progress,
        'done': done,
        'overdue': overdue
    }), 200
if __name__ == '__main__':
    import os

    # Add a default admin if none exists
    with app.app_context():
        if not User.query.filter_by(email='admin@test.com').first():
            hashed_pw = generate_password_hash('admin123')
            admin = User(name='Admin', email='admin@test.com', password=hashed_pw, role='ADMIN')
            db.session.add(admin)
            db.session.commit()
            print("Default admin created: admin@test.com / admin123")

    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

