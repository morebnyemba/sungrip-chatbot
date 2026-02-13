import { atom } from 'jotai';
import { atomWithStorage } from 'jotai/utils';

const ACCESS_TOKEN_KEY = 'accessToken';
const REFRESH_TOKEN_KEY = 'refreshToken';
const USER_DATA_KEY = 'user';

export const accessTokenAtom = atomWithStorage(ACCESS_TOKEN_KEY, null);
export const refreshTokenAtom = atomWithStorage(REFRESH_TOKEN_KEY, null);
export const userAtom = atomWithStorage(USER_DATA_KEY, null);

export const isAuthenticatedAtom = atom((get) => !!get(accessTokenAtom));

export const isLoadingAuthAtom = atom(true);
