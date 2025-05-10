import React, { useState, useEffect, useRef } from 'react';
import { UserServiceClient } from '../proto/auth_grpc_web_pb';
import { 
  ListUsersRequest,
  UpdateUserRoleRequest,
  UserActivityRequest,
  SubscribeToUpdatesRequest
} from '../proto/auth_pb';
import '../styles/UserManagement.css';

const UserManagement = () => {
  const [users, setUsers] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedRole, setSelectedRole] = useState('all');
  const [activityLogs, setActivityLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const wsRef = useRef(null);

  const client = new UserServiceClient('http://localhost:50051');

  useEffect(() => {
    fetchUsers();
    fetchActivityLogs();
    setupWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const setupWebSocket = () => {
    wsRef.current = new WebSocket('ws://localhost:50051/ws/users');

    wsRef.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'USER_UPDATED') {
        setUsers(prevUsers => 
          prevUsers.map(user => 
            user.id === data.user.id ? data.user : user
          )
        );
      }
      if (data.type === 'ACTIVITY_LOG') {
        setActivityLogs(prevLogs => [data.log, ...prevLogs.slice(0, 49)]);
      }
    };

    wsRef.current.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    wsRef.current.onclose = () => {
      console.log('WebSocket disconnected');
    };
  };

  const fetchUsers = () => {
    setLoading(true);
    const request = new ListUsersRequest();
    client.listUsers(request, {}, (err, response) => {
      setLoading(false);
      if (err) {
        console.error(err);
        return;
      }
      setUsers(response.getUsersList().map(u => u.toObject()));
    });
  };

  const fetchActivityLogs = () => {
    const request = new UserActivityRequest();
    request.setLimit(50);
    client.getUserActivity(request, {}, (err, response) => {
      if (err) {
        console.error(err);
        return;
      }
      setActivityLogs(response.getLogsList().map(l => l.toObject()));
    });
  };

  const updateUserRole = (userId, newRole) => {
    const request = new UpdateUserRoleRequest();
    request.setUserId(userId);
    request.setNewRole(newRole);
    
    client.updateUserRole(request, {}, (err) => {
      if (err) {
        console.error(err);
        return;
      }
    });
  };

  const filteredUsers = users.filter(user => {
    const matchesSearch = user.email.toLowerCase().includes(searchTerm.toLowerCase()) || 
                         user.name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesRole = selectedRole === 'all' || user.role === selectedRole;
    return matchesSearch && matchesRole;
  });

  return (
    <div className="user-management-container">
      <div className="filters">
        <input
          type="text"
          placeholder="Search users..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
        <select 
          value={selectedRole} 
          onChange={(e) => setSelectedRole(e.target.value)}
        >
          <option value="all">All Roles</option>
          <option value="admin">Admin</option>
          <option value="manager">Manager</option>
          <option value="user">User</option>
        </select>
      </div>

      <div className="user-list">
        {loading ? (
          <p>Loading users...</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Role</th>
                <th>Last Active</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredUsers.map(user => (
                <tr key={user.id}>
                  <td>{user.name}</td>
                  <td>{user.email}</td>
                  <td>
                    <select 
                      value={user.role}
                      onChange={(e) => updateUserRole(user.id, e.target.value)}
                    >
                      <option value="admin">Admin</option>
                      <option value="manager">Manager</option>
                      <option value="user">User</option>
                    </select>
                  </td>
                  <td>{new Date(user.lastActive * 1000).toLocaleString()}</td>
                  <td>
                    <button>View Activity</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="activity-logs">
        <h3>Recent Activity</h3>
        <ul>
          {activityLogs.map(log => (
            <li key={log.id}>
              [{new Date(log.timestamp * 1000).toLocaleString()}] {log.userEmail}: {log.action}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};

export default UserManagement;