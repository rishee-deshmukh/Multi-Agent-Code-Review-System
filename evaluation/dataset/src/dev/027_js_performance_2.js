async function fetchUsers(userIds) {
    const users = [];

    for (const id of userIds) {
        const response = await fetch(`https://api.example.com/users/${id}`);  // @label io_in_loop high
        const user = await response.json();
        users.push(user);
    }

    return users;
}

module.exports = { fetchUsers };