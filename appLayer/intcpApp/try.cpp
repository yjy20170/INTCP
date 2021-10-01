/*
g++ appLayer/in*App/try.cpp -o appLayer/in*App/try
appLayer/in*App/try
*/

#include <iostream>
#include <stack>
#include <vector>
using namespace std;
bool IsPopOrder(vector<int> pushV,vector<int> popV) {
    stack<int> stk;
    int i = 0;
    int idx = 0;
    for(;i < pushV.size();i++){
        cout<<"入栈 "<<pushV[i]<<endl;
        if(pushV[i] == popV[idx]){
        	cout<<"出栈 "<<popV[idx]<<endl;
            idx++;
            while(!stk.empty() &&stk.top()==popV[idx]){
        	    cout<<"出栈 "<<popV[idx]<<endl;
                idx++;
                stk.pop();
            }
        }else{
            stk.push(pushV[i]);
        }
    }
    if(stk.empty()) return true;
    return false;
	
}
int main(){
    vector<int> pushV, popV;
    for(int i=0;i<5;i++){
        pushV.push_back(i);
    }
    popV.push_back(2);
    popV.push_back(1);
    popV.push_back(4);
    popV.push_back(0);
    popV.push_back(3);
    cout<<IsPopOrder(pushV,popV)<<endl;
}