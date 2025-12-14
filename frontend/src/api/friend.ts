/**
 * 好友管理 API 封装
 * Friend Management API Wrapper
 */
import axios from 'axios'

export interface FriendSearchResult {
    user_id: number
    username: string
    name: string
    role: string
    dept?: string
    is_friend: boolean
    has_pending_request: boolean
    request_direction?: 'sent' | 'received'
}

export interface FriendRequest {
    id: number
    from_user_id: number
    to_user_id: number
    message?: string
    status: string
    created_at: string
    updated_at: string
    from_user_name?: string
    from_user_username?: string
    to_user_name?: string
    to_user_username?: string
}

export interface FriendInfo {
    user_id: number
    username: string
    name: string
    role: string
    dept?: string
    status: string
    friendship_id: number
    friend_since: string
}

export const friendAPI = {
    /**
     * 搜索用户
     */
    searchUser: (keyword: string) => {
        return axios.get<{ code: number; data: { results: FriendSearchResult[] } }>(
            '/api/friend/search',
            { params: { keyword } }
        )
    },

    /**
     * 发送好友申请
     */
    sendRequest: (toUserId: number, message?: string) => {
        return axios.post('/api/friend/request/send', {
            to_user_id: toUserId,
            message
        })
    },

    /**
     * 获取收到的好友申请列表
     */
    getReceivedRequests: (statusFilter: string = 'pending') => {
        return axios.get<{ code: number; data: { requests: FriendRequest[]; total: number } }>(
            '/api/friend/request/list',
            { params: { status_filter: statusFilter } }
        )
    },

    /**
     * 获取发出的好友申请列表
     */
    getSentRequests: () => {
        return axios.get<{ code: number; data: { requests: FriendRequest[]; total: number } }>(
            '/api/friend/request/sent'
        )
    },

    /**
     * 处理好友申请（接受/拒绝）
     */
    processRequest: (requestId: number, action: 'accept' | 'reject') => {
        return axios.post('/api/friend/request/process', {
            request_id: requestId,
            action
        })
    },

    /**
     * 获取好友列表
     */
    getFriendList: () => {
        return axios.get<{ code: number; data: { friends: FriendInfo[]; total: number } }>(
            '/api/friend/list'
        )
    },

    /**
     * 删除好友
     */
    deleteFriend: (friendId: number) => {
        return axios.delete(`/api/friend/delete/${friendId}`)
    }
}
