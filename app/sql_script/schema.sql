--system constants Table
CREATE TABLE system_constants (
    id INT IDENTITY(1,1) PRIMARY KEY,
    type NVARCHAR(100),
    name NVARCHAR(255),
    status NVARCHAR(50),
    created_by NVARCHAR(255),
    created_at DATETIME DEFAULT GETDATE(),
    modified_by NVARCHAR(255),
    modified_at DATETIME,
    is_active BIT DEFAULT 1
);

-- Users Table
CREATE TABLE Users (
    user_id INT IDENTITY(1,1) PRIMARY KEY,
    username NVARCHAR(255) NOT NULL,
    status_id INT,
    created_by NVARCHAR(255),
    created_at DATETIME DEFAULT GETDATE(),
    modified_by NVARCHAR(255),
    modified_at DATETIME,
    is_active BIT DEFAULT 1,
    FOREIGN KEY (status_id) REFERENCES system_constants(id)  
);

-- Template Table
CREATE TABLE Template (
    template_id INT IDENTITY(1,1) PRIMARY KEY,
    template_name NVARCHAR(255),
    template_description NVARCHAR(MAX),
    created_by NVARCHAR(255),
    created_at DATETIME DEFAULT GETDATE(),
    modified_by NVARCHAR(255),
    modified_at DATETIME,
    is_active BIT DEFAULT 1
);

-- Projects Table
CREATE TABLE Projects (
    project_id INT IDENTITY(1,1) PRIMARY KEY,
    project_name NVARCHAR(255),
    project_description NVARCHAR(MAX),
    template_id INT,
    start_date DATE,
    end_date DATE,
    status_id INT,
    created_by NVARCHAR(255),
    created_at DATETIME DEFAULT GETDATE(),
    modified_by NVARCHAR(255),
    modified_at DATETIME,
    is_active BIT DEFAULT 1,
    FOREIGN KEY (template_id) REFERENCES Template(template_id),
    FOREIGN KEY (status_id) REFERENCES system_constants(id)  
);

-- Permissions Table
CREATE TABLE Permissions (
    permission_id INT IDENTITY(1,1) PRIMARY KEY,
    permission_type NVARCHAR(100),
    permission_bracket NVARCHAR(100),
    created_by NVARCHAR(255),
    created_at DATETIME DEFAULT GETDATE(),
    modified_by NVARCHAR(255),
    modified_at DATETIME,
    is_active BIT DEFAULT 1
);

-- Labels Table
CREATE TABLE labels (
    labels_id INT IDENTITY(1,1) PRIMARY KEY,
    label_text NVARCHAR(255),
    category_id INT,
    created_by NVARCHAR(255),
    created_at DATETIME DEFAULT GETDATE(),
    modified_by NVARCHAR(255),
    modified_at DATETIME,
    is_active BIT DEFAULT 1,
);

-- User_Permission_Mapping Table
CREATE TABLE User_Permission_Mapping (
    user_permission_mapping_id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT,
    permission_id INT,
    created_by NVARCHAR(255),
    created_at DATETIME DEFAULT GETDATE(),
    modified_by NVARCHAR(255),
    modified_at DATETIME,
    is_active BIT DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES Users(user_id),
    FOREIGN KEY (permission_id) REFERENCES Permissions(permission_id)
);

-- Template_task_mapping Table
CREATE TABLE Template_task_mapping (
    template_task_mapping_id INT IDENTITY(1,1) PRIMARY KEY,
    template_id INT,
    task_name NVARCHAR(255),
    priority_id INT,
    isMilestone BIT,
    dependent_taskid INT,
    dependency_type NVARCHAR(50),
    days_offset INT,
    parent_id INT,
    status_id INT,
    created_by NVARCHAR(255),
    created_at DATETIME DEFAULT GETDATE(),
    modified_by NVARCHAR(255),
    modified_at DATETIME,
    is_active BIT DEFAULT 1,
    FOREIGN KEY (template_id) REFERENCES Template(template_id),
    FOREIGN KEY (priority_id) REFERENCES system_constants(id),   
    FOREIGN KEY (status_id) REFERENCES system_constants(id),     
    FOREIGN KEY (dependent_taskid) REFERENCES Template_task_mapping(template_task_mapping_id),
    FOREIGN KEY (parent_id) REFERENCES Template_task_mapping(template_task_mapping_id)
);

-- Project_task_mapping Table
CREATE TABLE Project_task_mapping (
    project_task_mapping_id INT IDENTITY(1,1) PRIMARY KEY,
    project_id INT,
    task_name NVARCHAR(255),
    priority_id INT,
    isMilestone BIT,
    dependent_taskid INT,
    dependency_type NVARCHAR(50),
    days_offset INT,
    parent_id INT,
    start_date DATE,
    end_date DATE,
    status_id INT,
    created_by NVARCHAR(255),
    created_at DATETIME DEFAULT GETDATE(),
    modified_by NVARCHAR(255),
    modified_at DATETIME,
    is_active BIT DEFAULT 1,
    FOREIGN KEY (project_id) REFERENCES Projects(project_id),
    FOREIGN KEY (priority_id) REFERENCES system_constants(id),   
    FOREIGN KEY (status_id) REFERENCES system_constants(id),    
    FOREIGN KEY (dependent_taskid) REFERENCES Project_task_mapping(project_task_mapping_id),
    FOREIGN KEY (parent_id) REFERENCES Project_task_mapping(project_task_mapping_id)
);

-- user_task_mapping Table
CREATE TABLE user_task_mapping (
    user_task_mapping_id INT IDENTITY(1,1) PRIMARY KEY,
    task_id INT,
    user_id INT,
    created_by NVARCHAR(255),
    created_at DATETIME DEFAULT GETDATE(),
    modified_by NVARCHAR(255),
    modified_at DATETIME,
    is_active BIT DEFAULT 1,
    FOREIGN KEY (task_id) REFERENCES Project_task_mapping(project_task_mapping_id),
    FOREIGN KEY (user_id) REFERENCES Users(user_id)
);

CREATE TABLE labels_project_task_mapping (
    labels_project_task_mapping_id INT IDENTITY(1,1) PRIMARY KEY,
    label_id INT,
    project_id INT,
    task_id INT,
    project_label_category_id INT,
    created_by NVARCHAR(255),
    created_at DATETIME DEFAULT GETDATE(),
    modified_by NVARCHAR(255),
    modified_at DATETIME,
    is_active BIT DEFAULT 1,
    FOREIGN KEY (label_id) REFERENCES labels(labels_id),
    FOREIGN KEY (project_id) REFERENCES Projects(project_id),
    FOREIGN KEY (task_id) REFERENCES Project_task_mapping(project_task_mapping_id),
);

CREATE TABLE user_sorting_mapping (
    user_sorting_mapping_id INT IDENTITY(1,1) PRIMARY KEY,
    user_id      INT NOT NULL,
    project_id   INT NOT NULL,
    sort_order   INT NOT NULL,
    created_at   DATETIME DEFAULT GETDATE(),
    created_by   VARCHAR(100),
    modified_at  DATETIME,
    modified_by  VARCHAR(100),
    is_active    BIT NOT NULL DEFAULT 1
);



-- Indexes
CREATE INDEX IX_Users_status_id ON Users(status_id);
CREATE INDEX IX_Projects_template_id ON Projects(template_id);
CREATE INDEX IX_Projects_status_id ON Projects(status_id);
CREATE INDEX IX_User_Permission_Mapping_user_id ON User_Permission_Mapping(user_id);
CREATE INDEX IX_User_Permission_Mapping_permission_id ON User_Permission_Mapping(permission_id);
CREATE INDEX IX_Template_task_mapping_template_id ON Template_task_mapping(template_id);
CREATE INDEX IX_Template_task_mapping_priority_id ON Template_task_mapping(priority_id);
CREATE INDEX IX_Template_task_mapping_status_id ON Template_task_mapping(status_id);
CREATE INDEX IX_Project_task_mapping_project_id ON Project_task_mapping(project_id);
CREATE INDEX IX_Project_task_mapping_priority_id ON Project_task_mapping(priority_id);
CREATE INDEX IX_Project_task_mapping_status_id ON Project_task_mapping(status_id);
CREATE INDEX IX_user_task_mapping_task_id ON user_task_mapping(task_id);
CREATE INDEX IX_user_task_mapping_user_id ON user_task_mapping(user_id);
CREATE INDEX IX_labels_category_id ON labels(category_id);
CREATE INDEX IX_labels_project_task_mapping_label_id ON labels_project_task_mapping(label_id);
CREATE INDEX IX_labels_project_task_mapping_project_id ON labels_project_task_mapping(project_id);
CREATE INDEX IX_labels_project_task_mapping_task_id ON labels_project_task_mapping(task_id);
CREATE INDEX IX_labels_project_task_mapping_category_id ON labels_project_task_mapping(project_label_category_id);
CREATE INDEX idx_usr_sort_user
    ON user_sorting_mapping (user_id, sort_order);

CREATE INDEX idx_usr_sort_project
    ON user_sorting_mapping (project_id);


INSERT INTO system_constants (type, name, status, created_by, is_active) VALUES
('USER_STATUS', 'Active', 'ACTIVE', 'SYSTEM', 1),
('USER_STATUS', 'Inactive', 'ACTIVE', 'SYSTEM', 1),
('USER_STATUS', 'Suspended', 'ACTIVE', 'SYSTEM', 1),
('USER_STATUS', 'Invited', 'ACTIVE', 'SYSTEM', 1),

('PROJECT_STATUS', 'Not Started', 'ACTIVE', 'SYSTEM', 1),
('PROJECT_STATUS', 'In Progress', 'ACTIVE', 'SYSTEM', 1),
('PROJECT_STATUS', 'On Hold', 'ACTIVE', 'SYSTEM', 1),
('PROJECT_STATUS', 'Completed', 'ACTIVE', 'SYSTEM', 1),
('PROJECT_STATUS', 'Cancelled', 'ACTIVE', 'SYSTEM', 1),

('TASK_STATUS', 'Not Started', 'ACTIVE', 'SYSTEM', 1),
('TASK_STATUS', 'In Progress', 'ACTIVE', 'SYSTEM', 1),
('TASK_STATUS', 'In Review', 'ACTIVE', 'SYSTEM', 1),
('TASK_STATUS', 'Blocked', 'ACTIVE', 'SYSTEM', 1),
('TASK_STATUS', 'Completed', 'ACTIVE', 'SYSTEM', 1),
('TASK_STATUS', 'Cancelled', 'ACTIVE', 'SYSTEM', 1),

('TASK_PRIORITY', 'Low', 'ACTIVE', 'SYSTEM', 1),
('TASK_PRIORITY', 'Medium', 'ACTIVE', 'SYSTEM', 1),
('TASK_PRIORITY', 'High', 'ACTIVE', 'SYSTEM', 1),
('TASK_PRIORITY', 'Critical', 'ACTIVE', 'SYSTEM', 1),

('DEPENDENCY_TYPE', 'Before', 'ACTIVE', 'SYSTEM', 1),
('DEPENDENCY_TYPE', 'After', 'ACTIVE', 'SYSTEM', 1);

INSERT INTO System_constants (type, name, status, created_by, is_active) 
VALUES 
    ('LABEL_CATEGORY', 'Project Label', 'ACTIVE', 'SYSTEM', 1),
    ('LABEL_CATEGORY', 'Task Label', 'ACTIVE', 'SYSTEM', 1);
 
	INSERT INTO System_constants (type, name, status, created_by, is_active) 
VALUES 
	('PROJECT_LABEL_CATEGORY', 'Engineer', 'ACTIVE', 'SYSTEM', 1),
    ('PROJECT_LABEL_CATEGORY', 'Sales Rep', 'ACTIVE', 'SYSTEM', 1);


ALTER TABLE Project_task_mapping
ALTER COLUMN dependency_type INT;

ALTER TABLE Project_task_mapping
ADD sort_order INT NULL;

ALTER TABLE Project_task_mapping
ADD subtask_sort_order INT NULL;
 
ALTER TABLE Template_task_mapping
ALTER COLUMN dependency_type INT;

ALTER TABLE Projects
ADD sort_order INT NULL;

CREATE INDEX IX_Projects_sort_order ON Projects(sort_order);

ALTER TABLE Project_task_mapping
ADD sort_order INT NULL,          
    subtask_sort_order INT NULL;   

CREATE INDEX IX_Project_task_mapping_sort_order
    ON Project_task_mapping(sort_order);

CREATE INDEX IX_Project_task_mapping_subtask_sort_order
    ON Project_task_mapping(subtask_sort_order);

ALTER TABLE Template
ADD sort_order INT NULL;

ALTER TABLE Template_task_mapping
ADD sort_order INT NULL,
    subtask_sort_order INT NULL;

ALTER TABLE labels
ADD sort_order INT NULL;

-- Task-level label mappings (labels on a task)
ALTER TABLE labels_project_task_mapping
ADD sort_order INT NULL;

ALTER TABLE user_sorting_mapping
ADD CONSTRAINT fk_usr_sort_user
    FOREIGN KEY (user_id) REFERENCES users(user_id);

ALTER TABLE user_sorting_mapping
ADD CONSTRAINT fk_usr_sort_project
    FOREIGN KEY (project_id) REFERENCES projects(project_id);

ALTER TABLE user_sorting_mapping
ADD CONSTRAINT uq_usr_sort_user_project
    UNIQUE (user_id, project_id);

CREATE INDEX IX_Template_sort_order
    ON Template(sort_order);

CREATE INDEX IX_Template_task_mapping_sort_order
    ON Template_task_mapping(sort_order);

CREATE INDEX IX_Template_task_mapping_subtask_sort_order
    ON Template_task_mapping(subtask_sort_order);


CREATE INDEX IX_Template_sort_order
    ON labels(sort_order);

CREATE INDEX IX_Template_task_mapping_sort_order
    ON labels_project_task_mapping(sort_order);

DELETE FROM User_Permission_Mapping;   
DELETE FROM Permissions;

DBCC CHECKIDENT ('Permissions', RESEED, 0);
DBCC CHECKIDENT ('User_Permission_Mapping', RESEED, 0);

INSERT INTO Permissions (permission_type, permission_bracket, is_active)
VALUES
('PROJECT_CREATE',  'PROJECT',  1),
('PROJECT_EDIT',    'PROJECT',  1),
('PROJECT_DELETE',  'PROJECT', 1),
('PROJECT_READ',    'PROJECT',  1),

('TEMPLATE_CREATE', 'TEMPLATE',  1),
('TEMPLATE_EDIT',   'TEMPLATE', 1),
('TEMPLATE_DELETE', 'TEMPLATE',  1),
('TEMPLATE_READ',   'TEMPLATE', 1),

('USER_CREATE',     'USER',      1),
('USER_EDIT',       'USER',      1),
('USER_DELETE',     'USER',     1),
('USER_READ',       'USER',      1),

('LABEL_CREATE',    'LABEL',     1),
('LABEL_EDIT',      'LABEL',     1),
('LABEL_DELETE',    'LABEL',     1),
('LABEL_READ',      'LABEL',     1),

('MILESTONE_EDIT_DATE', 'MILESTONE',  1);


ALTER DATABASE [sqldb-tpm-prod]
SET CHANGE_TRACKING = ON;

 
ALTER TABLE dbo.user_task_mapping
ENABLE CHANGE_TRACKING
WITH (TRACK_COLUMNS_UPDATED = ON);

ALTER TABLE user_task_mapping
ADD RowVer ROWVERSION;


ALTER TABLE [Users]
ADD profile_picture VARCHAR(500);

PRINT 'Database created and seeded successfully!!!'