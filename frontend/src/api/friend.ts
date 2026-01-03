/**
 * 濂藉弸绠＄悊 API 灏佽
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
     * 鎼滅储鐢ㄦ埛
     */
    searchUser: (keyword: string) => {
        return axios.get<{ code: number; data: { results: FriendSearchResult[] } }>(
            '/friend/search',
            { params: { keyword } }
        )
    },

    /**
     * 鍙戦€佸ソ鍙嬬敵璇?
     */
    sendRequest: (toUserId: number, message?: string) => {
        return axios.post('/friend/request/send', {
            to_user_id: toUserId,
            message
        })
    },

    /**
     * 鑾峰彇鏀跺埌鐨勫ソ鍙嬬敵璇峰垪琛?
     */
    getReceivedRequests: (statusFilter: string = 'pending') => {
        return axios.get<{ code: number; data: { requests: FriendRequest[]; total: number } }>(
            '/friend/request/list',
            { params: { status_filter: statusFilter } }
        )
    },

    /**
     * 鑾峰彇鍙戝嚭鐨勫ソ鍙嬬敵璇峰垪琛?
     */
    getSentRequests: () => {
        return axios.get<{ code: number; data: { requests: FriendRequest[]; total: number } }>(
            '/friend/request/sent'
        )
    },

    /**
     * 澶勭悊濂藉弸鐢宠锛堟帴鍙?鎷掔粷锛?
     */
    processRequest: (requestId: number, action: 'accept' | 'reject') => {
        return axios.post('/friend/request/process', {
            request_id: requestId,
            action
        })
    },

    /**
     * 鑾峰彇濂藉弸鍒楄〃
     */
    getFriendList: () => {
        return axios.get<{ code: number; data: { friends: FriendInfo[]; total: number } }>(
            '/friend/list'
        )
    },

    /**
     * 鍒犻櫎濂藉弸
     */
    deleteFriend: (friendId: number) => {
        return axios.delete(`/api/friend/delete/${friendId}`)
    }
}

