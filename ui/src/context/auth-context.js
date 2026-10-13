import { createContext, useContext } from 'react';

const AuthContext = createContext(null)

const useAuthContext = () => {
   const context = useContext(AuthContext)

   if (context === null) {
      throw new Error("AuthContext can only be used inside a provider");    
   }
   return context
}

export {AuthContext, useAuthContext}